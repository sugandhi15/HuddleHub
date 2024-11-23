###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

from ..datatypes.curve import Curve
from ..datatypes.hlocv import HlocvCurve, Fields
from ..datatypes.table import Table

import numpy as np
import itertools
import string
import io

__all__ = [
    "TableExtract",
    "TableFilter",
    "TableFuncApply",
    "TableFuncApplyToColumn",
    "TableGroupBy",
    "TableFromCurves",
    "TableFromCsv",
    "TableToCsv",
]


# -----------------------------------------------------------------------------
def TableExtract(table, columns, new_names=None):
    """
    Description:
        Return a new sub-Table with the required columns.
    Inputs:
        table     - the input table
        columns   - a list of names of the columns to be extracted
        new_names - a list of new column names
    Returns:
        A new Table.
    """
    new_names = new_names or columns
    new_table = [new_names] + \
                [[row.__getattribute__(k) for k in columns] for row in table]

    return Table(new_table)


# -----------------------------------------------------------------------------
def TableFilter(table, func, in_place=True):
    """
    Description:
        Remove rows from the table based on a user-defined filter function
    Inputs:
        table    - the input table
        func     - user-defined function. Takes a row as input and returns
                   False if the row has to be excluded.
        in_place - if False, create a new table
    Returns:
        A new Table if in_place is False
    """
    if in_place:
        table.data = [row for row in table.data if func(row)]
        return table
    else:
        return Table([list(table.tags)] +
                     [row for row in table.data if func(row)])


# -----------------------------------------------------------------------------
def TableFuncApply(table, func, col_name):
    """
    Description:
        Return a new table with an extra column whose values are obtained
        applying the user-defined function to each row of the table.
    Inputs:
        table    - the input table
        func     - the user-defined function
        col_name - the name of the new column
    Returns:
        A new Table.
    """
    new_table = [list(table.tags) + [col_name]] + \
                [row.values + [func(row)] for row in table]

    return Table(new_table)


# -----------------------------------------------------------------------------
def TableFuncApplyToColumn(table, func, col_name):
    """
    Description:
        Applie in-place a user-defined function to a column of the table.
    Inputs:
        table    - the input table
        func     - the user-defined function
        col_name - the name of the column that is modified by the user-defined
                   function
    """
    for row in table.data:
        row[col_name] = func(row[col_name])
    return table


# -----------------------------------------------------------------------------
def TableGroupBy(table, pivot, measures):
    """
    Description:
        Create a pivot-table from the input table.
    Inputs:
        table    - the input table
        pivot    - column name used for vertical pivot aggregation
        measures - list of tuples in the form ( key, funcname ) where:
                     - key is the name of the column to be used as measure
                     - funcname is the aggregation function (SUM, COUNT,
                       AVG, STD, MIN, MAX)
    Returns:
        A new table.
    """
    # --- sort the table by vertical pivot
    table.sort((pivot, ))

    # --- arrays of tags and measure functions for pivot table
    tags = [pivot]
    fns = []
    for mkey, funcname in measures:
        funcname = funcname.upper()
        tags.append("{0:s}_{1:s}".format(mkey, funcname))
        if funcname == "SUM":
            fns.append(lambda g: sum([r[mkey] for r in g]))
        elif funcname == "COUNT":
            fns.append(lambda g: len([r[mkey] for r in g]))
        elif funcname == "AVG":
            fns.append(lambda g: np.mean([r[mkey] for r in g]))
        elif funcname == "STD":
            fns.append(lambda g: np.std([r[mkey] for r in g]))
        elif funcname == "MIN":
            fns.append(lambda g: min([r[mkey] for r in g]))
        elif funcname == "MAX":
            fns.append(lambda g: max([r[mkey] for r in g]))
        else:
            raise NameError("Unrecognized grouping "
                            "function {0:s}".format(funcname))

    # --- put together the pivot table
    pivot_table = [tags]
    for key, group in itertools.groupby(table.data, lambda r: r[pivot]):
        group = list(group)
        pivot_table.append([key] + [f(group) for f in fns])

    return Table(pivot_table)


# -----------------------------------------------------------------------------
def TableFromCurves(crvs, tags=None):
    """
    Description:
        Convert a list of curves into a table.
    Inputs:
        crvs - a list of curves
        tags - a list of names (Optional)
    Returns:
        A Table.
    """
    dates = set()
    for crv in crvs:
        dates.update(crv.dates)

    if tags is None:
        tab = [["Date"] + ["Curve{0:02d}".format(i) for i in range(len(crvs))]]
    else:
        tab = [["Date"] + tags]

    for d in sorted(dates):
        values = [d]
        for crv in crvs:
            try:
                if isinstance(crv, Curve):
                    values.append(crv[d])
                elif isinstance(crv, HlocvCurve):
                    values.append(crv[d][Fields.Close])
            except IndexError:
                values.append(None)
        tab.append(values)

    return Table(tab)


# -----------------------------------------------------------------------------
def TableFromCsv(file_name="", delimiter=","):
    """
    Description:
        Create a table from a csv text file. The first line of the file must
        define all the tags for the table (header).
    Inputs:
        file_name - the name of the csv file. The full path must be specified.
        delimiter - the character used to separate fields
    Returns:
        A Table.
    """
    tbl = []
    with open(file_name, "r") as csvfile:
        for line in csvfile:
            # --- split line, eliminating EOL and quotes and add to the
            #     table array
            row = line.rstrip().replace("\"", "").split(delimiter)
            tbl.append([r.strip() for r in row])

    # --- remove spaces and illegal characters form header
    trantab = string.maketrans("", "")
    header = tbl[0]
    for i, item in enumerate(header):
        header[i] = str(item).translate(trantab, " ?%/.=:")
    tbl[0] = header

    return Table(tbl)


# -----------------------------------------------------------------------------
def TableToCsv(table, file_name=None, delimiter=",", use_quotes=False):
    """
    Description:
        Write the content of a Table to a text file in csv format.
    Inputs:
        table      - the input table
        file_name  - the name of the HTML file. The full filepath must be
                     specified. If None, cStringIO.StringIO() is used and a
                     string with the csv table is returned.
        delimiter  - the character used to separate fields
        use_quotes - if True, wrap every record in double quotes
    Returns:
        A string with the Table in csv format if file_name is None.
    """
    if use_quotes:
        fstr = lambda x: '"{0!s}"'.format(x)
    else:
        fstr = lambda x: "{0!s}".format(x)

    if file_name is None:
        csvfile = io.StringIO()
    else:
        csvfile = open(file_name, "w")

    try:
        csvfile.writelines(delimiter.join(table.tags) + "\n")
        for row in table.data:
            txt = delimiter.join([fstr(item) for item in row.values])
            csvfile.writelines(txt + "\n")
        # --- if writing to StringIO, copy content into a string before
        #     releasing the resource
        if file_name is None:
            output = csvfile.getvalue()
        else:
            output = None
    finally:
        csvfile.close()

    return output
