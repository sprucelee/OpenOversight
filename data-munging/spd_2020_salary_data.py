#!/usr/bin/env python
import logging
from pathlib import Path

import click
import common
import numpy as np
import pandas as pd


log = logging.getLogger(__name__)


def match_salary_data(
    ids: pd.DataFrame, df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Match salary data based on name from the provided data.
    Returns the salary dataframe as well as officers that were not matched.
    """
    ids.columns = ["id", "last", "first"]
    # Remove Jr, IV, II, III, etc.
    df.loc[:, "Name"] = df.Name.replace(r" ?((Jr)|(II)|(III)|(IV))\.?", "", regex=True)
    # Split the name by comma, the first part is the last name
    df["last"] = df.Name.str.split(",").str[0]
    # The second part is the first name, but we only want the text *before* the
    # first space, because the rest includes the middle initial which we can ignore
    df["first"] = df.Name.str.split(",").str[1].str.split(" ").str[0]
    # Merge with prod data based on the first and last names
    merged = df.merge(ids, how="left", on=["last", "first"]).astype(
        {"id": pd.Int64Dtype()}
    )
    # Reduce to a subset of the columns
    merged = merged[["Name", "Base Pay", "Overtime", "first", "last", "id"]]
    # Split off the links that don't have an OpenOversight badge associated with them
    _has_id = merged["id"].notna()
    missing = merged[~_has_id]
    merged = merged[_has_id]
    # Reduce columns even more
    merged = merged[["Base Pay", "Overtime", "id"]]
    # Rename columns for OO
    merged.columns = ["salary", "overtime_pay", "officer_id"]
    # Add an empty id column
    merged["id"] = None
    # Set the year to 2020
    merged["year"] = 2020
    # Only save out records with an OO ID
    merged = merged[~merged.officer_id.isna()]
    # Convert the salary from "$###,###.##" to a float
    merged.loc[:, "salary"] = (
        merged["salary"].replace(r"[\$,]", "", regex=True).astype(float)
    )
    # Do the same for overtime pay, but overtime pay may also be null
    # so we have to do some special replacements so the float conversion works
    merged.loc[:, "overtime_pay"] = (
        merged["overtime_pay"]
        .replace(r"[\$, ]", "", regex=True)
        .replace("", np.nan)
        .astype(float)
    )
    return merged, missing


def main(id_path: Path, data: Path, output: Path):
    log.info("Starting import")
    df = pd.read_csv(data, usecols=["Name", "Base Pay", "Overtime"])
    ids = pd.read_csv(
        id_path,
        usecols=["id", "first name", "last name"],
    )
    merged, missing = match_salary_data(ids, df)
    common.write_files_with_missing(merged, missing, output)


@click.command()
@click.argument("id_path", type=click.Path(exists=True, path_type=Path))
@click.argument("data", type=click.Path(exists=True, path_type=Path))
@click.argument("output", type=click.Path(path_type=Path))
def cli(id_path: Path, data: Path, output: Path):
    logging.basicConfig(
        format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
        level=logging.INFO,
    )
    main(id_path, data, output)


if __name__ == "__main__":
    cli()
