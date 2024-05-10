import collections
from clldutils.misc import slug
from cldfbench import CLDFSpec, Dataset as BaseDataset
import pathlib
import re
from pyglottolog import Glottolog
from csvw.dsv import UnicodeWriter
import pybtex.database
from pycldf.sources import Source



LICENSES = {
        "": "All rights reserved",
        "Creative Commons License: Attribution-Noncommercial-No Derivative Works.": "CCBYNCND",
        "Creative Commons Attribution-ShareAlike 4.0 License": "CCBYSA-4.0",
        "Creative Commons Attribution license 4.0.": "CCBY-4.0",
        "public domain": "Public Domain",
        "Creative Commons Attribution-No Derivatives license 4.0.": "CCBYND-4.0",
        "Creative Commons Attribution Share-Alike license 4.0.": "CCBYSA",
        "restricted": "All rights reserved",
        "Creative Commons Attribution-Noncommercial-No Derivatives license 4.0.": "CCBYNCND-4.0",
        }
        

def bible_info(text):
    if " not found" in text:
        return 
    
    tables = re.findall(
            '<table border=.1. padding=.2.>(.*?)</table>', 
            text, 
            re.DOTALL)
    info = {
            "language": "",
            "language_en": "",
            "dialect": "",
            "title": "",
            "title_en": "",
            "abbreviation": "",
            "copyright": "",
            "translator": "",
            "license": "",
            "date": "",
            "year": "",
            }

    if not tables or len(tables) < 2:
        return info
    table = tables[0]
    for tr in re.findall("<tr>(.*?)</tr>", table, re.DOTALL):
        tds = re.findall("<td[^>]*>(.*?)</td>", tr, re.DOTALL)
        tds = [
                re.sub("<.*?>", "", td) for td in tds]
        if len(tds) == 1:
            info["copyright"] = tds[0]
        elif len(tds) > 1:
            if "Language:" in tds[0]:
                info["language"] = tds[1]
                if len(tds) > 2:
                    info["language_en"] = tds[2]
            if "Dialect:" in tds[0]:
                info["dialect"] = tds[1]
            if "Title:" in tds[0]:
                info["title"] = tds[1]
                if len(tds) > 2:
                    info["title_en"] = tds[2]
            if "Abbreviation:" in tds[0]:
                info["abbreviation"] = tds[2]

    # check for cc
    cc = ""
    if "creative commons" in text.lower():
        cc = re.findall(
                '([Cc]reative [Cc]ommons [^<]*)</a>',
                text,
                )
        if cc:
            cc = cc[0]
        else:
            cc = re.findall(
                    '(Creative Commons .*)',
                    text
                    )[0]
    elif "all rights reserved" in text.lower():
        cc = "restricted"
    elif "public domain" in text.lower():
        cc = "public domain"

    year = re.findall("©.*?([0-9][0-9][0-9][0-9])", text)
    if year:
        info["year"] = year[0]

    date = re.findall("([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])", text)
    if date:
        info["date"] = date[0]
    if "translation by" in text.lower():
        translator = re.findall("[tT]ranslation by: (.*?)<", text)
        if translator:
            info["translator"] = translator[0]
    elif "contributor" in text.lower():
        contributor = re.findall("[cC]ontributor: (.*?)<", text)
        if contributor:
            info["translator"] = contributor[0]


    info["license"] = LICENSES.get(cc, cc)
    return info





class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "biblesources"

    def cldf_specs(self):
        return CLDFSpec(
                dir=self.cldf_dir, module="Generic",
                metadata_fname="cldf-metadata.json"
                )

    def cmd_download(self, args):
        
        table = [[
            "ID",
            "Name",
            "Name_in_Source",
            "Variety",
            "ISO639P3Code",
            "Glottocode",
            "Family",
            "Latitude",
            "Longitude",
            "Macroarea",
            "Year",
            "Date",
            "Copyright",
            "License",
            "Translator",
            "Title",
            "URL"]]
        
        download_info = input("Download all information? (y/n) ")
        download_info = True if download_info == "y" else False

        if download_info:
            self.raw_dir.download(
                    "https://github.com/lgessler/pronto/raw/master/RELEASE_v0.1.md", 
                    "bible-sources.md")
            self.raw_dir.download(
                    "http://ebible.org/Scriptures/dir.php",
                    "bible-sources.html")
        
        gpath = input("Path to Glottolog? ")

        glottolog = Glottolog(gpath)
        iso2glot = glottolog.languoids_by_code()

        with open(self.raw_dir / "bible-sources.html") as f:
            text = f.read()
        bibles = re.findall(
                '<a href="(...)([^_]*)_html.zip">...[^_]*_html.zip</a>',
                text,
                )
        sources = []
        for iso, extension in bibles:
            args.log.info("processing {0} / {1}".format(iso, extension))
            if download_info:
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
                    suffix = "NONE"
                else:
                    suffix = extension
                path = pathlib.Path(iso + "_" + suffix + ".html")
                with open(self.raw_dir / "info" / path) as f:
                    text = f.read()
            info = bible_info(text)
            if info:
                language = iso2glot[iso]
                lid = slug(language.name) + slug(extension)
                bible_id = iso + extension
                table += [[
                    lid,
                    language.name,
                    info["language"],
                    info["dialect"],
                    iso,
                    language.glottocode,
                    language.family.name if language.family else "",
                    language.latitude or "",
                    language.longitude or "",
                    language.macroareas[0].name,
                    info["year"],
                    info["date"],
                    info["copyright"],
                    info["license"],
                    info["translator"],
                    info["title"],
                    "https://ebible.org/Scriptures/{0}_html.zip".format(
                        bible_id)]]
        with UnicodeWriter(self.raw_dir / "bibles.tsv", delimiter="\t") as writer:
            for row in table:
                writer.writerow(row)

    def cmd_makecldf(self, args):
        
        args.writer.cldf.add_component(
                "LanguageTable")
        args.writer.cldf.add_columns(
                "LanguageTable",
                {
                    "name": "Contribution_IDS",
                    "separator": " "},
                "Variety"
                )

        args.writer.cldf.add_component(
                "ContributionTable",
                "Language_ID",
                "Contribution_Type", # Olac types
                "Creator",
                "Year", # can we specify?
                "Contribution_Date", # can we specify?
                "License", # can we specify
                "Copyright", # can we specify
                "URL", # can we specify
                {
                    'name': 'Source', 
                    'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source', 
                    }
                )
        args.writer.cldf.add_foreign_key(
                "ContributionTable", "Language_ID",
                "LanguageTable", "ID")
        
        languages = collections.defaultdict(
                lambda : {
                    "ID": "",
                    "Name": "",
                    "Variety": "",
                    "ISO639P3Code": "",
                    "Glottocode": "",
                    "Family": "",
                    "Latitude": "",
                    "Longitude": "",
                    "Macroarea": "",
                    "Contribution_IDS": []}
                )
        contributions = collections.defaultdict(
                lambda : {
                    "ID": "",
                    "Name": "",
                    "Description": "",
                    "Language_ID": "",
                    "Contribution_Type": "Primary texts",
                    "Contributor": "ebible.org", # can make a full list
                    "Creator": "",
                    "Year": "",
                    "Contribution_Date": "",
                    "Citation": "",
                    "License": "",
                    "Copyright": "", 
                    "URL": "",
                    "Source": ""
                    }
                )
        sources = [] # stores pybtex entries
        for row in self.raw_dir.read_csv(
                "bibles.tsv", delimiter="\t", dicts=True):
            args.log.info("Adding {0}".format(row["Glottocode"]))
            
            lid = slug(row["Name"], lowercase=False)
            if row["Variety"]:
                lid += "-" + slug(row["Variety"], lowercase=False)
            languages[lid]["ID"] = lid
            languages[lid]["Name"] = row["Name"]
            languages[lid]["Variety"] = row["Variety"]
            languages[lid]["Latitude"] = row["Latitude"]
            languages[lid]["Longitude"] = row["Longitude"]
            languages[lid]["Macroarea"] = row["Macroarea"]
            languages[lid]["ISO639P3Code"] = row["ISO639P3Code"]
            languages[lid]["Glottocode"] = row["Glottocode"]
            languages[lid]["Family"] = row["Family"]
            languages[lid]["Contribution_IDS"] += [row["ID"]]
            
            citation = "{Translator} ({Year}): {Title} [The Bible in {Name}]. Makawao: ebible.org.  URL: {URL}"
            contributions[row["ID"]]["Citation"] = citation.format(**row)
            contributions[row["ID"]]["Creator"] = row["Translator"]
            contributions[row["ID"]]["Name"] = "Bible in {0}".format(row["Name"])
            contributions[row["ID"]]["Year"] = row["Year"]
            contributions[row["ID"]]["Description"] = "The Bible, translated into {0}.".format(row["Name"])
            contributions[row["ID"]]["Contribution_Date"] = row["Date"]
            contributions[row["ID"]]["License"] = row["License"]
            contributions[row["ID"]]["Copyright"] = row["Copyright"]
            contributions[row["ID"]]["URL"] = row["URL"]
            contributions[row["ID"]]["Source"] = "CLD-Bible-{0}".format(
                    row["ID"])
            contributions[row["ID"]]["ID"] = row["ID"]

            # create sources
            source = pybtex.database.Entry(type_="book")
            source.fields["editor"] = row["Translator"]
            source.fields["year"] = row["Year"]
            source.fields["title"] = row["Title"] + "[The Bible, translated into {0}]".format(row["Name"])
            source.fields["cld_contribution_id"] = row["ID"]
            source.fields["publisher"] = "ebible.org"
            source.fields["address"] = "Makawao"
            source.fields["url"] = row["URL"]
            source.fields["key"] = "CLD-Bible-{0}".format(row["ID"])
            sources.append(Source.from_entry(source.fields["key"], source))
        for language in languages.values():
            args.writer.objects["LanguageTable"].append(language)
        for contribution in contributions.values():
            args.writer.objects["ContributionTable"].append(contribution)
        args.writer.cldf.sources.add(*sources)

