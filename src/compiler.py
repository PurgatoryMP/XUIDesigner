# compiler.py
import xml.etree.ElementTree as ET
from xml.dom import minidom

class XUICompiler:
    @staticmethod
    def generate_xml(root_item):
        if not root_item:
            return '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'

        root_el = ET.Element(root_item.tag_name)
        XUICompiler._build_element(root_item, root_el)

        raw_str = ET.tostring(root_el, 'utf-8')
        parsed = minidom.parseString(raw_str)
        formatted = parsed.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')

        lines = [line for line in formatted.split('\n') if line.strip()]
        return '\n'.join(lines)

    @staticmethod
    def _build_element(xui_item, xml_element):
        for k, v in sorted(xui_item.attributes.items()):
            if str(v).strip() != "":
                xml_element.set(k, str(v))

        for child in xui_item.child_xui_items:
            child_el = ET.SubElement(xml_element, child.tag_name)
            XUICompiler._build_element(child, child_el)