# compiler.py

class XUICompiler:
    @staticmethod
    def generate_plain_xml(root_item):
        if not root_item:
            return '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'

        header = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        return header + XUICompiler._build_tree(root_item, as_html=False, selected_item=None, indent_lvl=0)

    @staticmethod
    def generate_rich_xml(root_item, selected_item):
        if not root_item:
            return '<pre style="color: #d4d4d4;">&lt;?xml version="1.0" encoding="utf-8" standalone="yes"?&gt;\n&lt;!-- Empty Layout --&gt;</pre>'

        header = '&lt;?xml version="1.0" encoding="utf-8" standalone="yes"?&gt;\n'
        body = XUICompiler._build_tree(root_item, as_html=True, selected_item=selected_item, indent_lvl=0)

        return f'<pre style="font-family: Consolas, monospace; font-size: 10pt; color: #d4d4d4;">{header}{body}</pre>'

    @staticmethod
    def _build_tree(item, as_html, selected_item, indent_lvl):
        indent = "    " * indent_lvl
        is_selected = as_html and (item == selected_item)

        res = ""
        hl_start = '<span style="background-color: #1e457c; font-weight: bold; color: #00ffcc;">'
        hl_end = '</span>'

        if is_selected:
            res += hl_start

        tag_name = item.tag_name
        if as_html:
            res += f"{indent}&lt;{tag_name}"
        else:
            res += f"{indent}<{tag_name}"

        export_geo = str(item.attributes.get("designer_export_geometry", "true")).lower() == "true"

        skip_keys = ["designer_export_geometry"]
        if not export_geo:
            skip_keys.extend(["left", "top", "right", "bottom", "width", "height"])

        attrs = []
        for k, v in sorted(item.attributes.items()):
            if k in skip_keys or str(v).strip() == "":
                continue

            val = str(v)
            if as_html:
                val = val.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            attrs.append(f'{k}="{val}"')

        if attrs:
            if len(attrs) <= 2:
                res += " " + " ".join(attrs)
            else:
                attr_indent = indent + " "
                res += "\n" + attr_indent + f"\n{attr_indent}".join(attrs)

        # CRITICAL FIX: Evaluate if the element has ANY children (visual, non-visual, or text)
        has_children = bool(item.child_xui_items) or bool(item.non_visual_children) or bool(item.inner_text)

        if not has_children:
            if as_html:
                res += " /&gt;\n"
            else:
                res += " />\n"
            if is_selected:
                res += hl_end
            return res

        # Open container tag
        if as_html:
            res += "&gt;\n"
        else:
            res += ">\n"

        if is_selected:
            res += hl_end

        # CRITICAL FIX #1: Output inner text cleanly
        if item.inner_text:
            text_val = item.inner_text
            if as_html:
                text_val = text_val.replace('<', '&lt;').replace('>', '&gt;')
            res += f"{indent}    {text_val}\n"

        # CRITICAL FIX #1: Rebuild non-visual dot tags (e.g. <button.commit_callback>)
        for nv_child in item.non_visual_children:
            nv_tag = nv_child['tag']
            nv_attrs = nv_child['attributes']
            attr_strs = []

            for k, v in sorted(nv_attrs.items()):
                val = str(v)
                if as_html:
                    val = val.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                attr_strs.append(f'{k}="{val}"')

            if attr_strs:
                if len(attr_strs) <= 2:
                    attr_str = " " + " ".join(attr_strs)
                else:
                    attr_indent = indent + "      "
                    attr_str = "\n" + attr_indent + f"\n{attr_indent}".join(attr_strs)
            else:
                attr_str = ""

            if as_html:
                res += f"{indent}    &lt;{nv_tag}{attr_str} /&gt;\n"
            else:
                res += f"{indent}    <{nv_tag}{attr_str} />\n"

        # Output standard visual children
        for child in item.child_xui_items:
            res += XUICompiler._build_tree(child, as_html, selected_item, indent_lvl + 1)

        # Close container tag
        if is_selected:
            res += hl_start

        if as_html:
            res += f"{indent}&lt;/{tag_name}&gt;\n"
        else:
            res += f"{indent}</{tag_name}>\n"

        if is_selected:
            res += hl_end

        return res