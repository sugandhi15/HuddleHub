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

import operator

__all__ = ["Table", "TableError"]


###############################################################################
class TableError(Exception):
    """
    Base class for all Table exceptions.
    """
    pass


# -----------------------------------------------------------------------------
def row_factory(tags):
    """
    Table's row factory: generates a class with a predefined set of attributes.
    """
    # --- make sure that all tags are strings
    for tag in tags:
        if not isinstance(tag, str):
            raise ValueError("Table tags must be strings")

    # --- convert tags to a tuple
    tags = tuple(tags)

    # --- the appropriate row class is created on the fly
    class table_raw(object):
        __slots__ = tags

        def __init__(self, values):
            for i, value in enumerate(values):
                self.__setattr__(tags[i], value)

        def __getitem__(self, attribute):
            return self.__getattribute__(attribute)

        def __setitem__(self, attribute, value):
            self.__setattr__(attribute, value)

        def __str__(self):
            return ", ".join([str(v) for v in self.values])

        @property
        def fields(self):
            return tags

        @property
        def values(self):
            return [self.__getattribute__(a) for a in tags]

        @property
        def str_values(self):
            return [str(self.__getattribute__(a)) for a in tags]

        def __getstate__(self):
            return self.values

        def __setstate__(self, state):
            for i, attr in enumerate(tags):
                self.__setattr__(attr, state[i])

        def __eq__(self, other):
            return tags == other.__slots__ and self.values == other.values

    # --- return the newly created class
    return table_raw


###############################################################################
class Table(object):
    """
    """
    __slots__ = ("tags", "data", "row_fmt", "row_cls")

    # -------------------------------------------------------------------------
    def __init__(self, table, col_width=20):
        """
        Description:
            Table Class: Creates a Table from an omogeneous list of tuples or
            lists.
        Input:
            table_array - an list of lists in the following format:
                          [ [ tag1, tag2, ..., tagN ],
                            [ val1, val2, ..., valN ],
                            [ ...                   ] ]
            col_width   - default column width used for printing
        """
        self.tags = tuple((str(s).replace(" ", "_") for s in table[0]))
        self.row_fmt = "".join(["{{{0:d}:{1:d}s}}  ".format(k, col_width)
                                for k in range(len(self.tags))])
        self.row_cls = row_factory(self.tags)
        self.data = [self.row_cls(row)
                     for (i, row) in enumerate(table) if i > 0]

    # -------------------------------------------------------------------------
    def to_list(self):
        """
        Convert a Table to a list of lists with a header.
        """
        return [self.tags] + [row.values for row in self.data]

    # -------------------------------------------------------------------------
    #  support serialization

    def __getstate__(self):
        return self.to_list()

    def __setstate__(self, state):
        self.__init__(state)

    # -------------------------------------------------------------------------
    def __len__(self):
        return len(self.data)

    # -------------------------------------------------------------------------
    def __str__(self):
        return "\n".join(
            [self.row_fmt.format(*self.tags)] +
            [self.row_fmt.format(*["-"*len(tag) for tag in self.tags])] +
            [self.row_fmt.format(*row.str_values) for row in self.data])

    # -------------------------------------------------------------------------
    def __getitem__(self, idx):
        """
        Get a row by index.
        """
        return self.data[idx]

    # -------------------------------------------------------------------------
    def __eq__(self, other):
        return self.tags == other.tags and self.data == other.data

    # -------------------------------------------------------------------------
    def append(self, values):
        self.data.append(self.row_cls(values))

    # -------------------------------------------------------------------------
    def column(self, tag):
        """
        Description:
            Returns a list of values for the required column.
        Inputs:
            tag - the tag corresponding to the column to be returned
        Returns:
            A list with the required column values.
        """
        return [row.__getattribute__(tag) for row in self.data]

    # -------------------------------------------------------------------------
    def sort(self, tags, reverse=False):
        """
        Description:
            Sort table in-place by specified tags.
        Inputs:
            tags    - a list of the tags corresponding to the columns to be
                      sorted
            reverse - if True, sorts in reverse order
        Returns:
            None.
        """
        self.data.sort(key=operator.attrgetter(*tags), reverse=reverse)

    # -------------------------------------------------------------------------
    def find(self, tag, value):
        """
        Description:
            Find all the matching rows. The search is done on the specified
            column's tag.
        Inputs:
            tag   - the tag corresponding to the column to be searched
            value - the value
        Returns:
            A list of matching table_raw objects.
        """
        return [row for row in self.data if row.__getattribute__(tag) == value]
