from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import numpy as np
import urllib
from io import StringIO
from IPython.display import display, HTML

def n_colors(nucleotide):
    """
    Returns a string format to print the nucleotide
    with its appropriate background color according to the Clustal Colour Scheme.
    """

    # Raw python background colors
    # References:
    # https://stackabuse.com/how-to-print-colored-text-in-python/
    # https://www.ditig.com/256-colors-cheat-sheet
    raw_colors = {
        "black": 0,
        "red": 9,
        "green": 10,
        "yellow": 11,
        "blue": 12,
        "white": 15,
    }

    # Define nulceotide colors dict
    n_colors_dict = {
        "blue": ["C"],
        "red": ["A"],
        "green": ["T"],
        "yellow": ["G"],
    }

    # Define background color based on which nucleotide was passed
    bkg_color = None
    letter_color = None
    for color in n_colors_dict:
        if nucleotide in n_colors_dict[color]:
            bkg_color = raw_colors[color]
            letter_color = color

    # If the nucleotide does not fall into the defined color categories,
    # make it white (e.g. "-")
    if bkg_color == None:
        bkg_color = raw_colors["white"]

    if letter_color is not None and letter_color in ["blue", "red"]:
        # Define textcolor as white for darker colors
        textcolor = raw_colors["white"]
    else:
        # Define textcolor as black
        textcolor = raw_colors["black"]

    return f"\033[38;5;{textcolor}m\033[48;5;{bkg_color}m{nucleotide}\033[0;0m"


def aa_colors(amino_acid):
    """
    Returns a string format to print the amino acid
    with its appropriate background color according to the Clustal Colour Scheme:
    http://www.jalview.org/help/html/colourSchemes/clustal.html
    """

    # Raw python background colors
    # References:
    # https://stackabuse.com/how-to-print-colored-text-in-python/
    # https://www.ditig.com/256-colors-cheat-sheet
    raw_colors = {
        "black": 0,
        "red": 9,
        "green": 10,
        "yellow": 11,
        "blue": 12,
        "cyan": 14,
        "magenta": 5,
        "pink": 13,
        "orange": 1,  # This is maroon because the system colors don't have orange
        "white": 15,
    }

    # Define amino acid colors dict according to http://www.jalview.org/help/html/colourSchemes/clustal.html
    aa_colors_dict = {
        "blue": ["A", "I", "L", "M", "F", "W", "V", "C"],  # hydrophobic AAs
        "red": ["K", "R"],  # positive charge
        "magenta": ["E", "D"],  # negative charge
        "green": ["N", "Q", "S", "T"],  # polar
        "pink": ["C"],  # cysteines
        "orange": ["G"],  # glycines
        "yellow": ["P"],  # prolines
        "cyan": ["H", "Y"],  # aromatic
    }

    # Define background color based on which amino acid was passed
    bkg_color = None
    letter_color = None
    for color in aa_colors_dict:
        if amino_acid in aa_colors_dict[color]:
            bkg_color = raw_colors[color]
            letter_color = color

    # If the amino acid does not fall into the defined color categories,
    # make it white (e.g. "-")
    if bkg_color == None:
        bkg_color = raw_colors["white"]

    if letter_color is not None and letter_color in [
        "blue",
        "red",
        "magenta",
        "orange",
    ]:
        # Define textcolor as white for darker colors
        textcolor = raw_colors["white"]
    else:
        # Define textcolor as black
        textcolor = raw_colors["black"]

    return f"\033[38;5;{textcolor}m\033[48;5;{bkg_color}m{amino_acid}\033[0;0m"


def get_uniprot_seqs(server, ensembl_ids):
    """
    Retrieve UniProt sequences based on Ensemsbl identifiers.

    Args:
    - server
    Link to UniProt REST API server.
    - ensembl_ids:
    One or more transcript Ensembl IDs (string or list of strings).

    Returns data frame with UniProt ID, gene name, organism, sequence, sequence length, and query ID.
    """

    # If a single UniProt ID is passed as string, convert to list
    if type(ensembl_ids) == str:
        ensembl_ids = [ensembl_ids]

    # Define query arguments
    # Columns documentation: https://www.uniprot.org/help/uniprotkb%5Fcolumn%5Fnames
    # from/to IDs documentation: https://www.uniprot.org/help/api_idmapping
    query_args = {
        "from": "ENSEMBL_TRS_ID",
        "to": "ACC",
        "format": "tab",
        "query": " ".join(ensembl_ids),
        "columns": "id,genes,organism,sequence,length",
    }
    # Reformat query arguments
    query_args = urllib.parse.urlencode(query_args)
    query_args = query_args.encode("ascii")

    # Submit query to UniProt server
    request = urllib.request.Request(server, query_args)

    # Read and clean up results
    with urllib.request.urlopen(request) as response:
        res = response.read()

    # Initiate data frame so empty df will be returned if no matches are found
    df = pd.DataFrame()

    try:
        # This will throw an EmptyDataError if no results were found
        df = pd.read_csv(StringIO(res.decode("utf-8")), sep="\t")

        if len(df.columns) == 6:
            # Rename columns
            df.columns = [
                "uniprot_id",
                "gene_name",
                "organism",
                "sequence",
                "sequence_length",
                "query",
            ]
        # Sometimes a seventh "isomap" column is returned.
        if len(df.columns) == 7:
            # Drop isoform column (last column)
            df = df.iloc[:, :-1]
            # Rename columns
            df.columns = [
                "uniprot_id",
                "gene_name",
                "organism",
                "sequence",
                "sequence_length",
                "query",
            ]

        # Split rows if two different UniProt IDs for a single query ID are returned
        df = df.assign(Query=df["query"].str.split(",")).explode("query")

    # If no results were found, do nothing (returns the empty data frame)
    except pd.errors.EmptyDataError:
        None

    return df


def get_uniprot_info(server, ensembl_ids, id_type):
    """
    Retrieve UniProt synonyms and description based on Ensemsbl identifiers.

    Args:
    - server          Link to UniProt REST API server.
    - ensembl_ids     One or more transcript Ensembl IDs (string or list of strings).
    - id_type         "Gene" or "Transcript"

    Returns data frame with UniProt ID, gene name, organism, sequence, sequence length, and query ID.
    """

    # If a single Ensembl ID is passed as string, convert to list
    if type(ensembl_ids) == str:
        ensembl_ids = [ensembl_ids]

    if id_type == "Gene":
        ens_id_type = "ENSEMBL_ID"
    elif id_type == "Transcript":
        ens_id_type = "ENSEMBL_TRS_ID"
    else:
        logging.warning(
            f"Ensembl_ID '{ensembl_ids}' was not recognized as either gene nor transcript. Gene name synonyms and description will not be fetched from UniProt."
        )
        return

    # Define query arguments
    # Columns documentation: https://www.uniprot.org/help/uniprotkb%5Fcolumn%5Fnames
    # from/to IDs documentation: https://www.uniprot.org/help/api_idmapping
    query_args = {
        "from": ens_id_type,
        "to": "ACC",
        "format": "tab",
        "query": " ".join(ensembl_ids),
        "columns": "id,genes(PREFERRED),genes,protein names,comment(FUNCTION)",
    }
    # Reformat query arguments
    query_args = urllib.parse.urlencode(query_args)
    query_args = query_args.encode("ascii")

    # Submit query to UniProt server
    request = urllib.request.Request(server, query_args)

    # Read and clean up results
    with urllib.request.urlopen(request) as response:
        res = response.read()

    # Initiate data frame so empty df will be returned if no matches are found
    df = pd.DataFrame()

    try:
        # This will throw an EmptyDataError if no results were found
        df = pd.read_csv(StringIO(res.decode("utf-8")), sep="\t")

        if len(df.columns) == 6:
            # Rename columns
            df.columns = [
                "uniprot_id",
                "primary_gene_name",
                "synonyms",
                "protein_names",
                "uniprot_description",
                "query",
            ]
        # Sometimes a seventh "isomap" column is returned.
        if len(df.columns) == 7:
            # Drop isoform column (last column)
            df = df.iloc[:, :-1]
            # Rename columns
            df.columns = [
                "uniprot_id",
                "primary_gene_name",
                "synonyms",
                "protein_names",
                "uniprot_description",
                "query",
            ]

        # Split gene names into list of strings
        df["synonyms"] = df["synonyms"].str.split(" ")

    # If no results were found, return None
    except pd.errors.EmptyDataError:
        return None

    return df


def wrap_cols_func(df, cols):
    """
    Function to wrap columns cols of a
    data frame df for easier reading.
    """
    for col in cols:
        df.loc[:, col] = df[col].str.wrap(30)

    return display(HTML(df.to_html().replace("\\n", "<br>")))


def rest_query(server, query, content_type):
    """
    Function to query a

    Args:
    - server
    Serve to query.
    - Query
    Query that is passed to server.
    - content_type
    Contect type requested from server.

    Returns server output.
    """

    r = requests.get(server + query, headers={"Content-Type": content_type})

    if not r.ok:
        raise RuntimeError(
            f"HTTP response status code {r.status_code}. "
            "Please double-check arguments and try again.\n"
        )

    if content_type == "application/json":
        return r.json()
    else:
        return r.text


def find_latest_ens_rel():
    """
    Returns the latest Ensembl release number.
    """
    url = "http://ftp.ensembl.org/pub/"
    html = requests.get(url)

    # Raise error if status code not "OK" Response
    if html.status_code != 200:
        raise RuntimeError(
            f"HTTP response status code {html.status_code}. Please try again."
        )

    soup = BeautifulSoup(html.text, "html.parser")
    # Find all releases
    releases = soup.body.findAll(text=re.compile("release-"))
    # Get release numbers
    rels = []
    for rel in releases:
        rels.append(rel.split("/")[0].split("-")[-1])

    # Find highest release number (= latest release)
    ENS_rel = np.array(rels).astype(int).max()

    return ENS_rel


def gget_species_options(release=None):
    """
    Function to find all available species core databases for gget.

    Args:
    - release   Ensembl release for which the databases are fetched.
                (Default: latest release.)

    Returns list of available core databases.
    """
    # Find latest Ensembl release
    ENS_rel = find_latest_ens_rel()

    # If release != None, use user-defined Ensembl release
    if release != None:
        # Do not allow user-defined release if it is higher than the latest release
        if release > ENS_rel:
            raise ValueError(
                "Defined Ensembl release number cannot be greater than latest release."
            )
        else:
            ENS_rel = release

    # Find all available databases
    url = f"http://ftp.ensembl.org/pub/release-{ENS_rel}/mysql/"
    html = requests.get(url)

    # Raise error if status code not "OK" Response
    if html.status_code != 200:
        raise RuntimeError(
            f"HTTP response status code {html.status_code}. Please try again."
        )

    soup = BeautifulSoup(html.text, "html.parser")

    # Return list of all available databases
    databases = []
    for subsoup in soup.body.findAll("a"):
        if "core" in subsoup["href"]:
            databases.append(subsoup["href"].split("/")[0])

    return databases


def ref_species_options(which, release=None):
    """
    Function to find all available species for gget ref.

    Args:
    - release   Ensembl release for which available species should be fetched.
    - which     Which type of FTP. Possible entries: 'dna', 'cdna', 'gtf'.

    Returns list of available species.
    """
    # Find latest Ensembl release
    ENS_rel = find_latest_ens_rel()

    # If release != None, use user-defined Ensembl release
    if release != None:
        # Do not allow user-defined release if it is higher than the latest release
        if release > ENS_rel:
            raise ValueError(
                "Defined Ensembl release number cannot be greater than latest release."
            )
        else:
            ENS_rel = release

    # Find all available species for this release and FTP type
    if which == "gtf":
        url = f"http://ftp.ensembl.org/pub/release-{ENS_rel}/gtf/"
    if which == "dna" or which == "cdna":
        url = f"http://ftp.ensembl.org/pub/release-{ENS_rel}/fasta/"
    html = requests.get(url)

    # Raise error if status code not "OK" Response
    if html.status_code != 200:
        raise RuntimeError(
            f"HTTP response status code {html.status_code}. Please try again."
        )

    # Parse the html and generate a clean list of the available genomes
    soup = BeautifulSoup(html.text, "html.parser")

    sps = []
    for subsoup in soup.body.findAll("a"):
        sps.append(subsoup["href"].split("/")[0])

    species_list = sps[1:]

    # Return list of all available species
    return species_list


def parse_blast_ref_page(handle):
    """
    Extract RID and RTOE from the NCBI 'please wait' page.
    RTOE = 'Estimated time fo completion.'
    RID = 'Request ID'.

    Returns RID, RTOE

    Code partly adapted from the Biopython BLAST NCBIWWW project written
    by Jeffrey Chang (Copyright 1999), Brad Chapman, and Chris Wroe distributed under the
    Biopython License Agreement and BSD 3-Clause License
    https://github.com/biopython/biopython/blob/171697883aca6894f8367f8f20f1463ce7784d0c/LICENSE.rst
    """

    # Decode handle
    string = handle.read().decode()

    # Find RID
    idx = string.find("RID =")
    if idx == -1:
        rid = None
    else:
        jdx = string.find("\n", idx)
        rid = string[idx + len("RID =") : jdx].strip()

    # Find RTOE
    rtoe_idx = string.find("RTOE =")
    if rtoe_idx == -1:
        rtoe = None
    else:
        rtoe_jdx = string.find("\n", rtoe_idx)
        rtoe = string[rtoe_idx + len("RTOE =") : rtoe_jdx].strip()

    # If neither RID, nor RTOE were found, try to extract error message from HTML page
    if not rid and not rtoe:
        # Search for 'error msInf' div class
        i = s.find('<div class="error msInf">')
        if i != -1:
            msg = s[i + len('<div class="error msInf">') :].strip()
            msg = msg.split("</div>", 1)[0].split("\n", 1)[0].strip()
            if msg:
                raise ValueError("Error message from NCBI: %s" % msg)
        # Search for 'error' class
        i = s.find('<p class="error">')
        if i != -1:
            msg = s[i + len('<p class="error">') :].strip()
            msg = msg.split("</p>", 1)[0].split("\n", 1)[0].strip()
            if msg:
                raise ValueError("Error message from NCBI: %s" % msg)
        # Generic search for error messages
        i = s.find("Message ID#")
        if i != -1:
            # Break the message at the first HTML tag
            msg = s[i:].split("<", 1)[0].split("\n", 1)[0].strip()
            raise ValueError("Error message from NCBI: %s" % msg)
        # Raise general error, if the error layout was not recognized
        raise ValueError(
            "No request ID and no estimated time to completion were found in the NCBI 'please wait' page."
        )
    # Raise error if RTOE was found but RID was not
    elif not rid:
        raise ValueError(
            f"No request ID (RID) was found in the NCBI 'please wait' page. (Although estimated time to completion = {rtoe}.)"
        )
    # Raise error if RTOE was found but RID was not
    elif not rtoe:
        raise ValueError(
            f"No estimated time to completion was found in the NCBI 'please wait' page. (Although request ID = {rid}.)"
        )

    try:
        return rid, int(rtoe)
    except ValueError:
        raise ValueError(
            f"A non-integer estimated time to completion was found in the NCBI 'please wait' page: '{rtoe}'."
        )