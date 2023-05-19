from ebooklib import epub, ITEM_DOCUMENT
from ebooklib.epub import EpubItem, EpubBook, EpubHtml
from bs4 import BeautifulSoup
import subprocess


menopause = "/Users/mpfammatter/Calibre Library/Jennifer Gunter/The Menopause Manifesto (29)/The Menopause Manifesto - Jennifer Gunter.epub"
antiracist = "/Users/mpfammatter/Calibre Library/Ibram X. Kendi/How to Be an Antiracist (7)/How to Be an Antiracist - Ibram X. Kendi.epub"


book = epub.read_epub(menopause)
documents = book.get_items_of_type(ITEM_DOCUMENT)

for document in documents:
    if document.get_type() == ITEM_DOCUMENT:
        soup = BeautifulSoup(document.get_body_content(), 'html.parser')
        # pprint(str(soup))
        # break
        
        navs = [nav for nav in soup.find_all("nav")]
        for nav in navs:
            links = [link for link in soup.find_all('a')]
            for link in links:
                print(link)

# items[0].get_body_content()
chapter = book.get_item_with_href("e9780806540672_c10.xhtml")
soup = BeautifulSoup(chapter.get_body_content(), 'html.parser')
subprocess.run("pbcopy", text=True, input=soup.getText())