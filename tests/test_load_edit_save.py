from TexSoup import TexSoup
from tests.config import pancake


########################
# LOAD EDIT SAVE TESTS #
########################


def test_load_save(pancake):
    """Tests whether a LaTeX document can be loaded and saved."""
    soup = TexSoup(pancake)
    treated_pancake = str(soup)
    assert treated_pancake == pancake


def test_load_edit_save(pancake):
    """Tests whether a LaTeX document can be loaded, modified and saved."""
    soup = TexSoup(pancake)
    emph = soup.find('emph')
    emph.delete()
    pancake_no_emph_soup = str(soup)
    pancake_no_emph_replace = pancake.replace(r'\emph{Enjoy your meal!}', '')
    assert pancake_no_emph_soup == pancake_no_emph_replace
