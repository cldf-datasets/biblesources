import collections
from clldutils.misc import slug
from cldfbench import CLDFSpec, Dataset as BaseDataset
import pathlib
import re
from pyglottolog import Glottolog

INITIAL_PASS = True
PRONTO = False
DOWNLOAD_INFO = False

def get_license(text):
    tables = re.findall("<table[^>]*>(.*?)</table>", text, re.DOTALL)
    if not tables or len(tables) < 2:
        return "", ""
    table = tables[1]
    trs = re.findall("<tr>(.*?)</tr>", table, re.DOTALL)
    lic = re.findall("<[^>]*>([^<]*)</[^>]*>", trs[-1])[0]

    # check for cc
    if "Creative Commons" in text:
        cc = re.findall(
                '(Creative Commons [^<]*)</a>',
                text,
                )
        if cc:
            cc = cc[0]
        else:
            cc = re.findall(
                    '(Creative Commons .*)',
                    text
                    )[0]
    else:
        cc = ""
    return lic, cc


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "biblesources"

    def cldf_specs(self):
        return CLDFSpec(
                dir=self.cldf_dir, module="Generic",
                metadata_fname="cldf-metadata.json"
                )

    def cmd_download(self, args):


        if INITIAL_PASS:
            #self.raw_dir.download(
            #        "https://github.com/lgessler/pronto/raw/master/RELEASE_v0.1.md", 
            #        "bible-sources.md")
            #self.raw_dir.download(
            #        "http://ebible.org/Scriptures/dir.php",
            #        "bible-sources.html")
            #gpath = input("Path to Glottolog? ")
            #gpath = "/home/mattis/data/datasets/glottolog"
            with open(self.raw_dir / "bible-sources.html") as f:
                text = f.read()
            bibles = re.findall(
                    '<a href="(...)([^_]*)_html.zip">...[^_]*_html.zip</a>',
                    text,
                    )
            licenses = collections.defaultdict(list)
            for iso, extension in bibles:
                # get information

                args.log.info("downloading {0} / {1}".format(iso, extension))
                if DOWNLOAD_INFO:
                    self.raw_dir.download(
                        "http://ebible.org/find/details.php?id=" + iso + extension,
                        "tempfile.html")
                    with open(self.raw_dir / "tempfile.html") as f:
                        text = f.read()
                    if not extension:
                        extension = "NONE"
                    path = pathlib.Path(iso + "_" + extension + ".html")

                    with open(self.raw_dir / "info" / path, "w") as f:
                        f.write(text)
                else:
                    if not extension:
                        extension = "NONE"
                    path = pathlib.Path(iso + "_" + extension + ".html")
                    with open(self.raw_dir / "info" / path) as f:
                        text = f.read()
                lic, cc = get_license(text)
                if cc:
                    licenses[cc] += [(iso, extension)]
                else:
                    licenses[lic] += [(iso, extension)]
                    
            for line, values in sorted(licenses.items(), key=lambda x:
                                       len(x[1])):
                if len(values) > 1:
                    print(line, len(values))
            
        if PRONTO:
            glottolog = Glottolog(gpath)
            iso2glot = glottolog.languoids_by_code()
            table = []
            with open(self.raw_dir / "bible-sources.md") as f:
                start = False
                visited = set()
                for line in f:
                    if line.startswith("# Datasets"):
                        start = True
                    elif start:
                        pronto = line.split(")")[0][6:].split(" ")[0]
                        isocode = line.split("[")[2].split("]")[0]
                        if isocode in iso2glot:
                            language = iso2glot[isocode]
                            lid = slug(language.name)
                            variants = list("123456789")
                            has_variant = False
                            if lid in visited:
                                has_variant = True
                                while True:
                                    new_lid = lid + variants.pop(0)
                                    if new_lid not in visited:
                                        lid = new_lid
                                        break
                            else:
                                visited.add(lid)
                                
                            table += [[
                                lid,
                                language.name,
                                "1" if has_variant else "",
                                language.glottocode,
                                language.family.name if language.family else "",
                                isocode,
                                pronto]]
                        else:
                            args.log.info("Missing iso-code {0}".format(isocode))
            with open(self.etc_dir / "languages.tsv", "w") as f:
                f.write("ID\tName\tHasVariant\tGlottocode\tFamily\tISO639P3Code\tPRONTO\n")
                for row in table:
                    f.write("\t".join(row) + "\n")

