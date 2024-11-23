###############################################################################
#
#   Copyright: (c) 2015-2018 Carlo Sbraccia
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

from onyx.core import StringField, DictField

from .ufo_book import Book

__all__ = ["Broker"]


###############################################################################
class Broker(Book):
    """
    Class used to represent a broker.
    """
    BookType = StringField(default="Broker")
    FeeSchedule = DictField()


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing

    brokers = [
        AddIfMissing(Broker(Name="TEST_BROKER")),
        AddIfMissing(Broker(Name="BROKER-SUSPENSE")),
    ]

    return [broker.Name for broker in brokers]
