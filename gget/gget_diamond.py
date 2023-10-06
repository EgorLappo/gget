import logging
import subprocess
import sys
import platform
import os
import pandas as pd
import uuid

# DIAMOND and ELM id for temporary files
RANDOM_ID = str(uuid.uuid4())


from .compile import PACKAGE_PATH

# Path to precompiled diamond binary
if platform.system() == "Windows":
    PRECOMPILED_DIAMOND_PATH = os.path.join(
        PACKAGE_PATH, f"bins/{platform.system()}/diamond.exe"
    )
else:
    PRECOMPILED_DIAMOND_PATH = os.path.join(
        PACKAGE_PATH, f"bins/{platform.system()}/diamond"
    )


def tsv_to_df(tsv_file, headers=None):
    """
    Convert tsv file to dataframe format

    Args:
    tsv_file - file to be converted

    Returns:
    df -  dataframe

    """

    try:
        df = pd.DataFrame()
        if headers:
            df = pd.read_csv(tsv_file, sep="\t", names=headers)
        else:
            # ELM Instances.tsv file had 5 lines before headers and data
            df = pd.read_csv(tsv_file, sep="\t", skiprows=5)
        return df

    except pd.errors.EmptyDataError:
        logging.warning(f"Query did not result in any matches.")
        return None


def create_input_file(sequences):
    """
    Copy sequences to a temporary fasta file for DIAMOND alignment

    Args:
    sequences - list of user input amino acid sequences

    Returns: input file absolute path
    """
    # print(f"sequences for input file{sequences}")
    if type(sequences) == str:
        sequences = [sequences]

    with open(f"tmp_{RANDOM_ID}.fa", "w") as f:
        for idx, seq in enumerate(sequences):
            f.write(f">Seq {idx}\n{seq}\n")

    return f"tmp_{RANDOM_ID}.fa"
    # check if correct sequences are written to file
    # try:
    #     with open(f"{os.getcwd()}tmp_{RANDOM_ID}.fa", 'r') as f:
    #         print(f.read())
    # except:
    #     continue


def remove_temp_files():
    """
    Delete temporary files

    Args:
    input       - Input fasta file containing amino acid sequences
    out         - Output tsv file containing the output returned by DIAMOND
    reference   - Reference database binary file produced by DIAMOND

    Returns:
    None
    """
    if os.path.exists(f"tmp_{RANDOM_ID}_out.tsv"):
        os.remove(f"tmp_{RANDOM_ID}_out.tsv")
    if os.path.exists("reference.dmnd"):
        os.remove("reference.dmnd")
    if os.path.exists("tmp_{RANDOM_ID}.fa"):
        os.remove("tmp_{RANDOM_ID}.fa")


def diamond(
    sequences,
    reference,
    json=False,
    verbose=True,
    out=None,
    sensitivity="very-sensitive",
):
    """
    Perform protein sequence alignment using DIAMOND for multiple sequences

    Args:
     - input          Input sequences path and file name (include ,fa) in FASTA file format
     - reference      Reference file path and file name (include .fa) in FASTA file format
     - json           If True, returns results in json format instead of data frame. Default: False.
     - out            folder name to save two resulting csv files. Default: results (default: None).
     - verbose        True/False whether to print progress information. Default True.
     - sensitivity    The sensitivity can be adjusted using the options --fast, --mid-sensitive, --sensitive, --more-sensitive, --very-sensitive and --ultra-sensitive.

    Returns DIAMOND output in tsv format
    """
    # TODO: --very_sensitive and makedb --in as args
    # if out is None, create temp file and delete once get dataframe
    # if make

    input_file = create_input_file(sequences)
    output = f"tmp_{RANDOM_ID}_out.tsv"

    if out is None:
        command = f"{PRECOMPILED_DIAMOND_PATH} makedb --quiet --in {reference} -d reference \
            && {PRECOMPILED_DIAMOND_PATH} blastp --quiet -q {input_file} -d reference -o {output} --{sensitivity} --ignore-warnings"
    else:
        output = out
        # The double-quotation marks allow white spaces in the path, but this does not work for Windows
        command = f"{PRECOMPILED_DIAMOND_PATH} makedb --quiet --in {reference} -d reference \
            && {PRECOMPILED_DIAMOND_PATH} blastp --quiet -q {input_file} -d reference -o {out}.tsv --{sensitivity} --ignore-warnings"
    # Run diamond command and write command output
    with subprocess.Popen(command, shell=True, stderr=subprocess.PIPE) as process_2:
        stderr_2 = process_2.stderr.read().decode("utf-8")
        # Log the standard error if it is not empty
        if stderr_2:
            sys.stderr.write(stderr_2)
    # Exit system if the subprocess returned wstdout = sys.stdout

    if process_2.wait() != 0:
        #TODO: change error message 
        logging.error(
            """
            DIAMOND failed. 
            """
        )
        return
    else:
        if verbose:
            logging.info(f"DIAMOND run complete.")
    # try:
    #     with open(f"{os.getcwd()}/out.fa", 'r') as f:
    #         print(f.read())
    # except:
    #     pass
    # print(f"Input file: {input_file}")
    # print(f"Reference file: {reference}")
    # print(f"Output file: {output}")

    df_diamond = tsv_to_df(
        output,
        [
            "query_accession",
            "target_accession",
            "Per. Ident",
            "length",
            "mismatches",
            "gap_openings",
            "query_start",
            "query_end",
            "target_start",
            "target_end",
            "e-value",
            "bit_score",
        ],
    )
    remove_temp_files()
    return df_diamond
