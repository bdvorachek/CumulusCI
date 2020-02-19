from typing import Sequence, Union
from lxml import etree


METADATA_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"


def _add_namespace(tag):
    return "{%s}%s" % (METADATA_NAMESPACE, tag)


def parse(source):
    return MetadataElement(etree.parse(source).getroot())


class MetadataElement:
    __slots__ = ["_element", "_parent", "tag"]

    def __init__(self, element: etree._Element, parent: etree._Element = None):
        assert isinstance(element, etree._Element)
        self._element = element
        self._parent = parent
        self.tag = element.tag.split("}")[1]

    @property
    def text(self):
        if len(self._element):
            return self._wrap_element(self._element.find(_add_namespace("text")))
        else:
            return self._element.text

    def _wrap_element(self, child: etree._Element):
        return MetadataElement(child, self._element)

    @text.setter
    def text(self, text):
        self._element.text = text

    def _get_child(self, childname):
        child_element = self._element.find(_add_namespace(childname))
        if child_element is None:
            raise AttributeError(f"{childname} not found in {self.tag}")
        return self._wrap_element(child_element)

    def _create_child(self, tag, text=None):
        element = etree.Element(_add_namespace(tag))
        element.text = text
        return self._wrap_element(element)

    def __getattr__(self, childname):
        return self._get_child(childname)

    def __getitem__(self, item: Union[int, str]):
        if isinstance(item, int):
            children = self._parent.findall(self._element.tag)
            print(children, self._parent, self._element)
            return self._wrap_element(children[item])
        elif isinstance(item, str):
            return self._get_child(item)

    def append(self, tag: str, text: str = None):
        newchild = self._create_child(tag, text)
        same_elements = self._element.findall(self._element.tag)
        if same_elements:
            last = same_elements[-1]
            self._element.insert(last.index() + 1, newchild._element)
        else:
            self._element.append(newchild._element)
        return newchild

    def insert(self, index: int, tag: str, text: str = None):
        newchild = self._create_child(tag, text)
        self._element.insert(index, newchild._element)
        return newchild

    def insertBefore(self, oldElement: "MetadataElement", tag: str, text: str = None):
        index = self._element.index(oldElement._element)
        newchild = self._create_child(tag, text)
        self._element.insert(index, newchild._element)
        return newchild

    def insertAfter(self, oldElement: "MetadataElement", tag: str, text: str = None):
        index = self._element.index(oldElement._element)
        newchild = self._create_child(tag, text)
        self._element.insert(index + 1, newchild._element)
        return newchild

    def extend(self, iterable: Sequence):
        self._element.extend(newchild._element for newchild in iterable)

    def remove(self, metadata_element):
        self._element.remove(metadata_element._element)

    def find(self, tag, text=None):
        return next(self._findall(tag, text), None)

    def findall(self, tag, text=None):
        return list(self._findall(tag, text))

    def _findall(self, type, text=None):
        def matches(e):
            if text:
                return e.text == text
            else:
                return True

        return (
            self._wrap_element(e)
            for e in self._element.findall(_add_namespace(type))
            if matches(e)
        )

    def tostring(self, **kwargs):
        kwargs = dict(encoding="unicode", pretty_print=True, **kwargs)
        return etree.tostring(self._element, pretty_print=True, encoding="unicode")

    def __eq__(self, other: "MetadataElement"):
        return self._element == other._element

    def __repr__(self):
        return f"<{self.tag}>{self.text}</{self.tag}> element"


def test_metadata_element():
    filename = "/Users/pprescod/code/NPSP/src/layouts/Account-Household Layout.layout"
    Layout = parse(filename)
    assert Layout.tag == "Layout"
    assert Layout["layoutSections"] == Layout.layoutSections
    layoutItem = Layout.layoutSections[0].layoutColumns[1].layoutItems[1]
    layoutItem2 = Layout["layoutSections"][0]["layoutColumns"][1]["layoutItems"][1]
    assert layoutItem == layoutItem2
    assert layoutItem.behavior.text == "Edit"

    layoutItem.field.text = "some_field"
    assert "<field>" in layoutItem.tostring()
    layoutColumn = Layout.layoutSections[0].layoutColumns[1]
    assert len(layoutColumn.findall("layoutItems")) == 2


from io import StringIO


def test_insertions():
    data = StringIO(
        f"""<Data xmlns='{METADATA_NAMESPACE}'><Foo>foo1</Foo><Foo>foo2</Foo></Data>"""
    )
    Data = parse(data)

    assert Data.Foo[0].text == "foo1"
    assert Data.Foo[1].text == "foo2"

    foo4 = Data.append("Foo", "foo4")
    assert Data.Foo[2].text == "foo4"
    assert Data.find(tag="Foo", text="foo4") == foo4

    Data.insertBefore(foo4, tag="Foo", text="foo3")
    assert Data.Foo[2].text == "foo3"
    Data.insertAfter(foo4, tag="Foo", text="foo5")
    assert Data.Foo[4].text == "foo5"


def test_text():
    data = StringIO(
        f"""<Data xmlns='{METADATA_NAMESPACE}'>
            <foo>Foo</foo>
            <text>Bar</text>
            <text>
                <bar>Bar2</bar>
            </text>
        </Data>"""
    )
    Data = parse(data)
    assert isinstance(Data.foo.text, str)
    assert Data.foo.text == "Foo"
    assert isinstance(Data.text.text, str)
    assert Data.text.text.lower() == "bar"
    assert Data.text[1].bar.text.lower() == "bar2"


def test_append_goes_in_the_middle():
    data = StringIO(
        f"""<Data xmlns='{METADATA_NAMESPACE}'>
            <foo>Foo</foo>
            <bar>Bar</bar>
        </Data>"""
    )
    Data = parse(data)
    Data.append(tag="foo", text="Foo2")
    assert Data.foo[1].text == "Foo2"
    Data.append(tag="foo", text="Foo3")
    assert Data.foo[2].text == "Foo3"
    Data.append(tag="bar", text="Bar2")
    assert Data.bar[1].text == "Bar2"


if __name__ == "__main__":
    test_metadata_element()
    test_text()
    test_append_goes_in_the_middle()
