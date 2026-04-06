#!/usr/bin/env python3
"""Benchmark TexSoup and related LaTeX tools on real arXiv sources.

Examples:
    python benchmarks/arxiv.py 2004.05565
    python benchmarks/arxiv.py 2004.05565 1706.03762 --repeats 3 --warmups 1
    python benchmarks/arxiv.py 2004.05565 --backends texsoup latexwalker plastex
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import importlib
import io
import json
import logging
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import traceback
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TexSoup import TexSoup

ARXIV_SOURCE_URL = 'https://arxiv.org/e-print/{paper_id}'
MARKER_FILE = '.ready'
SUPPORTED_TEX_SUFFIXES = ('.tex', '.ltx')

BACKEND_CONFIG = {}


def parse_texsoup(text, root):
    del root
    return TexSoup(text, tolerance=0)


def parse_latexwalker(text, root):
    del root
    module = importlib.import_module('pylatexenc.latexwalker')
    walker = module.LatexWalker(text)
    return walker.get_latex_nodes(pos=0)


def parse_plastex(text, root):
    module = importlib.import_module('plasTeX.TeX')
    with working_directory(root):
        tex = module.TeX()
        tex.input(text)
        return tex.parse()


def write_backend_input(prefix, text):
    workspace_root = REPO_ROOT / 'tmp' / 'benchmark_backends'
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=prefix, dir=workspace_root))
    input_path = workspace / 'input.tex'
    input_path.write_text(text)
    return workspace, input_path


def merge_perl5lib(extra):
    parts = []
    if extra:
        parts.append(extra)
    existing = os.environ.get('PERL5LIB')
    if existing:
        parts.append(existing)
    return ':'.join(part for part in parts if part)


def parse_latexml(text, root):
    latexml_bin = BACKEND_CONFIG.get('latexml_bin')
    if not latexml_bin:
        raise RuntimeError('latexml executable not configured')

    workspace, input_path = write_backend_input('.latexml-', text)
    output_path = workspace / 'output.xml'
    env = os.environ.copy()
    perl5lib = merge_perl5lib(BACKEND_CONFIG.get('latexml_perl5lib'))
    if perl5lib:
        env['PERL5LIB'] = perl5lib

    try:
        completed = subprocess.run(
            [
                str(latexml_bin),
                '--quiet',
                '--destination=%s' % output_path,
                str(input_path),
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=BACKEND_CONFIG.get('command_timeout_seconds', 30),
            check=False,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(message or 'latexml failed with exit code %s' % completed.returncode)
    return completed


def parse_latex2html(text, root):
    latex2html_bin = BACKEND_CONFIG.get('latex2html_bin')
    if not latex2html_bin:
        raise RuntimeError('latex2html executable not configured')

    workspace, input_path = write_backend_input('.latex2html-', text)
    output_dir = workspace / 'out'
    env = os.environ.copy()
    latex2html_dir = BACKEND_CONFIG.get('latex2html_dir')
    if latex2html_dir:
        env['LATEX2HTMLDIR'] = str(latex2html_dir)
    texinputs = env.get('TEXINPUTS', '')
    env['TEXINPUTS'] = '%s:%s' % (root, texinputs)

    try:
        completed = subprocess.run(
            [
                str(latex2html_bin),
                '-mkdir',
                '-dir',
                str(output_dir),
                str(input_path),
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=BACKEND_CONFIG.get('command_timeout_seconds', 30),
            check=False,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(message or 'latex2html failed with exit code %s' % completed.returncode)
    return completed


BACKENDS = {
    'texsoup': {
        'parser': parse_texsoup,
        'package': None,
        'kind': 'fault-tolerant parser',
    },
    'latexwalker': {
        'parser': parse_latexwalker,
        'package': 'pylatexenc',
        'kind': 'lightweight syntax walker',
    },
    'plastex': {
        'parser': parse_plastex,
        'package': 'plasTeX',
        'kind': 'LaTeX compiler / DOM builder',
    },
    'latexml': {
        'parser': parse_latexml,
        'package': None,
        'kind': 'LaTeX to XML converter',
    },
    'latex2html': {
        'parser': parse_latex2html,
        'package': None,
        'kind': 'LaTeX to HTML converter',
    },
}


def parse_args(argv=None, default_backends=None):
    parser = argparse.ArgumentParser(
        description='Download arXiv sources and benchmark LaTeX backends on the same input.'
    )
    parser.add_argument(
        'paper_ids',
        nargs='+',
        help='arXiv IDs or arXiv abstract URLs to benchmark.',
    )
    parser.add_argument(
        '--backends',
        nargs='+',
        choices=tuple(BACKENDS),
        default=list(default_backends or BACKENDS),
        help='Backends to benchmark.',
    )
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('tmp/arxiv_benchmarks'),
        help='Where downloaded and extracted sources are stored.',
    )
    parser.add_argument(
        '--repeats',
        type=int,
        default=3,
        help='Number of timed runs per backend and paper.',
    )
    parser.add_argument(
        '--warmups',
        type=int,
        default=1,
        help='Number of untimed warmup runs per backend and paper.',
    )
    parser.add_argument(
        '--skip-expand-inputs',
        action='store_true',
        help='Benchmark only the detected main .tex file without inlining imports.',
    )
    parser.add_argument(
        '--skip-expand-bbl',
        action='store_true',
        help='Do not inline .bbl files at \\bibliography commands.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Print the full result set as JSON after the human-readable summary.',
    )
    parser.add_argument(
        '--latexml-bin',
        type=Path,
        default=None,
        help='Path to the latexml executable or built script.',
    )
    parser.add_argument(
        '--latexml-perl5lib',
        default=None,
        help='Extra PERL5LIB to use when invoking latexml.',
    )
    parser.add_argument(
        '--latex2html-bin',
        type=Path,
        default=None,
        help='Path to the latex2html executable.',
    )
    parser.add_argument(
        '--latex2html-dir',
        type=Path,
        default=None,
        help='Value to export as LATEX2HTMLDIR when invoking latex2html.',
    )
    parser.add_argument(
        '--command-timeout-seconds',
        type=int,
        default=30,
        help='Timeout for external command backends such as latexml and latex2html. Use 0 to disable the timeout.',
    )
    return parser.parse_args(argv)


def normalize_paper_id(value):
    value = value.strip()
    match = re.search(r'arxiv\.org/abs/([^?#]+)', value)
    if match:
        value = match.group(1)
    value = value.removeprefix('arXiv:')
    return value


def slugify_paper_id(paper_id):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', paper_id)


def ensure_downloaded(paper_id, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / slugify_paper_id(paper_id) / 'source'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    url = ARXIV_SOURCE_URL.format(paper_id=paper_id)
    try:
        with urlopen(url) as response:
            destination.write_bytes(response.read())
    except HTTPError as exc:
        raise RuntimeError('Failed to download %s: HTTP %s' % (paper_id, exc.code))
    except URLError as exc:
        raise RuntimeError('Failed to download %s: %s' % (paper_id, exc.reason))
    return destination


def safe_extract(tar, destination):
    destination = destination.resolve()
    for member in tar.getmembers():
        member_path = (destination / member.name).resolve()
        if not str(member_path).startswith(str(destination)):
            raise RuntimeError('Unsafe tar member path: %s' % member.name)
    try:
        tar.extractall(destination, filter='data')
    except TypeError:
        tar.extractall(destination)


def clear_directory(path):
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def ensure_extracted(source_path):
    extraction_dir = source_path.parent / 'extracted'
    marker_path = extraction_dir / MARKER_FILE
    if marker_path.exists():
        return extraction_dir

    extraction_dir.mkdir(parents=True, exist_ok=True)
    clear_directory(extraction_dir)

    if tarfile.is_tarfile(source_path):
        with tarfile.open(source_path) as archive:
            safe_extract(archive, extraction_dir)
    else:
        raw = source_path.read_bytes()
        if raw.startswith(b'\x1f\x8b'):
            raw = gzip.decompress(raw)
        (extraction_dir / 'source.tex').write_bytes(raw)

    marker_path.write_text('ok\n')
    return extraction_dir


def iter_tex_files(root):
    files = []
    for suffix in SUPPORTED_TEX_SUFFIXES:
        files.extend(path for path in root.rglob('*%s' % suffix) if path.is_file())
    return sorted(set(files))


def read_text(path):
    return path.read_text(encoding='utf-8', errors='ignore')


def arg_string(arg):
    return getattr(arg, 'string', str(arg))


def pick_main_tex(root):
    candidates = []
    for path in iter_tex_files(root):
        text = read_text(path)
        has_docclass = r'\documentclass' in text
        has_begin_document = r'\begin{document}' in text
        has_title = r'\title' in text
        candidates.append((
            has_docclass and has_begin_document,
            has_docclass,
            has_title,
            len(text),
            path,
        ))
    if not candidates:
        raise RuntimeError('No .tex files found under %s' % root)
    return sorted(candidates, reverse=True)[0][-1]


def resolve_target(base_dir, raw_target):
    raw_target = raw_target.strip()
    candidates = [base_dir / raw_target]
    if not Path(raw_target).suffix:
        candidates.append(base_dir / ('%s.tex' % raw_target))
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def load_bibliography_text(current_file, soup, visited):
    current_dir = current_file.parent
    candidates = []
    for bibliography in soup.find_all('bibliography'):
        for arg in bibliography.args:
            for raw_name in arg_string(arg).split(','):
                raw_name = raw_name.strip()
                if not raw_name:
                    continue
                candidate = resolve_target(current_dir, raw_name)
                if candidate is None and not raw_name.endswith('.bbl'):
                    candidate = resolve_target(current_dir, '%s.bbl' % raw_name)
                if candidate is not None and candidate.suffix == '.bbl':
                    candidates.append(candidate)

    if not candidates:
        same_stem = current_file.with_suffix('.bbl')
        if same_stem.exists():
            candidates.append(same_stem)
        else:
            bbl_files = sorted(current_dir.glob('*.bbl'))
            if len(bbl_files) == 1:
                candidates.append(bbl_files[0])

    snippets = []
    for candidate in candidates:
        if candidate in visited:
            continue
        visited.add(candidate)
        snippets.append(read_text(candidate))
    return '\n'.join(snippets).strip()


def expand_tex(path, expand_bbl=True, visited=None):
    path = path.resolve()
    if visited is None:
        visited = set()
    if path in visited:
        return ''
    visited.add(path)

    text = read_text(path)
    soup = TexSoup(text, tolerance=1)

    for command_name in ('subimport', 'import', 'include', 'input'):
        for node in list(soup.find_all(command_name)):
            replacement = None
            if command_name == 'subimport' and len(node.args) >= 2:
                folder = arg_string(node.args[0])
                filename = arg_string(node.args[1])
                target = resolve_target(path.parent / folder, filename)
            else:
                if not node.args:
                    continue
                target = resolve_target(path.parent, arg_string(node.args[0]))
            if target is not None:
                replacement = expand_tex(target, expand_bbl=expand_bbl, visited=visited)
            if replacement is not None:
                node.replace_with(replacement)

    if expand_bbl:
        bbl_text = load_bibliography_text(path, soup, visited)
        if bbl_text:
            for bibliography in list(soup.find_all('bibliography')):
                bibliography.replace_with(bbl_text)

    return repr(soup)


def quiet_call(fn, *args, **kwargs):
    stdout = io.StringIO()
    stderr = io.StringIO()
    logging_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            value = fn(*args, **kwargs)
    finally:
        logging.disable(logging_disable)
    return value, stdout.getvalue(), stderr.getvalue()


@contextlib.contextmanager
def working_directory(path):
    cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


def backend_version(name):
    if name == 'texsoup':
        module = importlib.import_module('TexSoup')
        return getattr(module, '__version__', 'unknown')
    if name == 'latexml':
        latexml_bin = BACKEND_CONFIG.get('latexml_bin')
        if not latexml_bin:
            return None
        env = os.environ.copy()
        perl5lib = merge_perl5lib(BACKEND_CONFIG.get('latexml_perl5lib'))
        if perl5lib:
            env['PERL5LIB'] = perl5lib
        completed = subprocess.run(
            [str(latexml_bin), '--VERSION'],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return (completed.stdout or completed.stderr).strip() or 'unknown'
    if name == 'latex2html':
        latex2html_bin = BACKEND_CONFIG.get('latex2html_bin')
        if not latex2html_bin:
            return None
        completed = subprocess.run(
            [str(latex2html_bin), '-version'],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.stdout or completed.stderr:
            return (completed.stdout or completed.stderr).splitlines()[0].strip()
        return 'unknown'
    package = BACKENDS[name]['package']
    try:
        metadata = importlib.import_module('importlib.metadata')
    except ImportError:
        import importlib_metadata as metadata
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def is_backend_available(name):
    if name == 'texsoup':
        return True
    if name == 'latexml':
        path = BACKEND_CONFIG.get('latexml_bin')
        return bool(path and Path(path).exists())
    if name == 'latex2html':
        path = BACKEND_CONFIG.get('latex2html_bin')
        return bool(path and Path(path).exists())
    module_name = {
        'latexwalker': 'pylatexenc.latexwalker',
        'plastex': 'plasTeX.TeX',
    }[name]
    try:
        importlib.import_module(module_name)
    except ImportError:
        return False
    return True


def run_backend(name, text, root, warmups, repeats):
    parser = BACKENDS[name]['parser']
    for _ in range(warmups):
        quiet_call(parser, text, root)

    timings_ms = []
    logs = []
    for _ in range(repeats):
        start = perf_counter()
        _, stdout, stderr = quiet_call(parser, text, root)
        timings_ms.append((perf_counter() - start) * 1000)
        if stdout or stderr:
            logs.append((stdout + stderr).strip())
    return {
        'ok': True,
        'version': backend_version(name),
        'kind': BACKENDS[name]['kind'],
        'timings_ms': [round(value, 3) for value in timings_ms],
        'mean_ms': round(statistics.mean(timings_ms), 3),
        'median_ms': round(statistics.median(timings_ms), 3),
        'min_ms': round(min(timings_ms), 3),
        'max_ms': round(max(timings_ms), 3),
        'log_excerpt': logs[-1][:400] if logs else '',
        'error': None,
    }


def maybe_run_backend(name, text, root, warmups, repeats):
    if not is_backend_available(name):
        return {
            'ok': False,
            'version': None,
            'kind': BACKENDS[name]['kind'],
            'timings_ms': [],
            'mean_ms': None,
            'median_ms': None,
            'min_ms': None,
            'max_ms': None,
            'log_excerpt': '',
            'error': 'Dependency not installed',
        }
    try:
        return run_backend(name, text, root, warmups, repeats)
    except Exception as exc:
        return {
            'ok': False,
            'version': backend_version(name),
            'kind': BACKENDS[name]['kind'],
            'timings_ms': [],
            'mean_ms': None,
            'median_ms': None,
            'min_ms': None,
            'max_ms': None,
            'log_excerpt': '',
            'error': '%s: %s' % (type(exc).__name__, exc),
            'traceback_tail': '\n'.join(traceback.format_exc().strip().splitlines()[-6:]),
        }


def load_paper_text(paper_id, args):
    source_path = ensure_downloaded(paper_id, args.cache_dir)
    extraction_dir = ensure_extracted(source_path)
    main_tex = pick_main_tex(extraction_dir)
    main_text = read_text(main_tex)

    if args.skip_expand_inputs:
        benchmark_text = main_text
        expanded = False
    else:
        benchmark_text = expand_tex(main_tex, expand_bbl=not args.skip_expand_bbl)
        expanded = True

    return {
        'paper_id': paper_id,
        'source_bytes': source_path.stat().st_size,
        'tex_file_count': len(iter_tex_files(extraction_dir)),
        'main_tex': str(main_tex.relative_to(extraction_dir)),
        'main_chars': len(main_text),
        'benchmark_chars': len(benchmark_text),
        'benchmark_lines': benchmark_text.count('\n') + 1,
        'expanded_source': expanded,
        'expanded_bbl': expanded and not args.skip_expand_bbl,
        'root': extraction_dir,
        'text': benchmark_text,
    }


def benchmark_paper(paper_id, args):
    paper = load_paper_text(paper_id, args)
    comparisons = {}
    for name in args.backends:
        comparisons[name] = maybe_run_backend(
            name,
            paper['text'],
            paper['root'],
            warmups=args.warmups,
            repeats=args.repeats,
        )
    del paper['root']
    del paper['text']
    paper['backends'] = comparisons
    return paper


def detect_built_latexml():
    candidates = sorted(REPO_ROOT.glob('tmp/cpan-home/work/*/LaTeXML-*/blib/script/latexml'))
    return candidates[-1] if candidates else None


def detect_built_latexml_perl5lib():
    latexml_bin = detect_built_latexml()
    if not latexml_bin:
        return None
    source_root = latexml_bin.parents[2]
    parts = [
        str(source_root / 'blib/lib'),
        str(REPO_ROOT / 'tmp/perl5/lib/perl5'),
        str(REPO_ROOT / 'tmp/perl5/lib/perl5/darwin-thread-multi-2level'),
    ]
    return ':'.join(path for path in parts if Path(path).exists())


def detect_latex2html_bin():
    path_hit = shutil.which('latex2html')
    if path_hit:
        return Path(path_hit)
    candidate = REPO_ROOT / 'tmp/latex2html-install/bin/latex2html'
    return candidate if candidate.exists() else None


def detect_latex2html_dir():
    if os.environ.get('LATEX2HTMLDIR'):
        return Path(os.environ['LATEX2HTMLDIR'])
    candidate = REPO_ROOT / 'tmp/latex2html-install'
    return candidate if candidate.exists() else None


def configure_backends(args):
    latexml_bin = args.latexml_bin or shutil.which('latexml')
    if latexml_bin:
        latexml_bin = Path(latexml_bin)
    else:
        latexml_bin = detect_built_latexml()

    latex2html_bin = args.latex2html_bin or detect_latex2html_bin()
    latex2html_dir = args.latex2html_dir or detect_latex2html_dir()

    BACKEND_CONFIG.update({
        'latexml_bin': latexml_bin,
        'latexml_perl5lib': args.latexml_perl5lib or detect_built_latexml_perl5lib(),
        'latex2html_bin': latex2html_bin,
        'latex2html_dir': latex2html_dir,
        'command_timeout_seconds': (
            None if args.command_timeout_seconds <= 0 else args.command_timeout_seconds
        ),
    })


def print_summary(results):
    for result in results:
        print('Paper:', result['paper_id'])
        print('  main tex:', result['main_tex'])
        print('  expanded source:', 'yes' if result['expanded_source'] else 'no')
        print('  source bytes:', result['source_bytes'])
        print('  tex files:', result['tex_file_count'])
        print('  benchmark chars:', result['benchmark_chars'])
        print('  benchmark lines:', result['benchmark_lines'])
        for backend_name, backend in result['backends'].items():
            version = backend['version'] or 'n/a'
            status = 'ok' if backend['ok'] else backend['error']
            print(
                '  {name} [{version}, {kind}]: {status}'.format(
                    name=backend_name,
                    version=version,
                    kind=backend['kind'],
                    status=status,
                )
            )
            if backend['ok']:
                print(
                    '    run ms (mean/median/min/max): '
                    '{mean_ms}/{median_ms}/{min_ms}/{max_ms}'.format(**backend)
                )
            if backend.get('log_excerpt'):
                print('    log excerpt:', backend['log_excerpt'].replace('\n', ' ')[:240])
        print()


def main(argv=None, default_backends=None):
    args = parse_args(argv=argv, default_backends=default_backends)
    configure_backends(args)
    results = []
    for raw_paper_id in args.paper_ids:
        results.append(benchmark_paper(normalize_paper_id(raw_paper_id), args))
    print_summary(results)
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
