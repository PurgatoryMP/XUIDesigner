"""
This module provides the XUICompiler class, responsible for serializing the in-memory
XUIGraphicsItem layout hierarchy back into valid XML source strings. It handles
multi-file layouts by compiling external referenced files into distinct outputs and
maps visual canvas selections and validation states to precise line numbers.
"""

from typing import Any, Dict, List, Optional, Tuple


class XUICompiler:
    """Compiler for converting XUIGraphicsItem hierarchies into XUI XML source files.

    Handles multi-file serialization, formatting clean XML indentation, filtering
    out design-time geometry attributes when appropriate, and generating line-number
    mappings for editor highlighting and error reporting.
    """

    @staticmethod
    def generate_source(
        root_item: Optional[Any], selected_item: Optional[Any]
    ) -> Dict[str, Tuple[str, Dict[str, List[Any]]]]:
        """Compiles XUI across ALL nested files.

        Recursively traverses the element hierarchy starting from `root_item`, building
        formatted XML strings for each referenced source file while tracking the exact
        starting and ending line numbers of selected items, errors, and warnings.

        Args:
            root_item: The top-level XUIGraphicsItem representing the root layout container.
            selected_item: The currently selected XUIGraphicsItem on the canvas, if any.

        Returns:
            A dictionary mapping filenames to a tuple containing:
                - The compiled XML string.
                - A dictionary of selection and validation line mappings:
                    {
                        'selected': [(start_line, end_line), ...],
                        'errors': [(start_line, end_line, [error_strs]), ...],
                        'warnings': [(start_line, end_line, [warning_strs]), ...]
                    }
        """
        files: Dict[str, Dict[str, Any]] = {}

        def init_file(filename: str) -> None:
            """Initializes the data structure for a new output file if not already present.

            Args:
                filename: The target output filename (e.g., 'layout.xml').
            """
            if filename not in files:
                files[filename] = {
                    'lines': ['<?xml version="1.0" encoding="utf-8" standalone="yes"?>'],
                    'selections': {'selected': [], 'errors': [], 'warnings': []},
                }

        def _build_lines(item: Any, indent_lvl: int) -> None:
            """Recursively generates XML lines for an item and its children.

            Args:
                item: The current XUIGraphicsItem being compiled.
                indent_lvl: The current indentation level (depth in the XML tree).
            """
            fname = getattr(item, 'source_file', 'layout.xml')
            init_file(fname)

            lines = files[fname]['lines']
            selections = files[fname]['selections']
            start_line = len(lines)
            indent = "    " * indent_lvl

            tag_name = item.tag_name

            # Determine whether absolute geometry should be exported or stripped
            export_geo = (
                str(item.attributes.get("designer_export_geometry", "true")).lower()
                == "true"
            )
            skip_keys = ["designer_export_geometry"]
            if not export_geo:
                skip_keys.extend(["left", "top", "right", "bottom", "width", "height"])

            # Filter and sort XML attributes
            attrs = []
            for k, v in sorted(item.attributes.items()):
                if k in skip_keys or str(v).strip() == "":
                    continue
                attrs.append(f'{k}="{v}"')

            # Format opening tag: inline if 2 or fewer attributes, multiline otherwise
            if attrs:
                if len(attrs) <= 2:
                    tag_open = f"{indent}<{tag_name} " + " ".join(attrs)
                else:
                    attr_indent = indent + " "
                    tag_open = (
                        f"{indent}<{tag_name}\n{attr_indent}"
                        + f"\n{attr_indent}".join(attrs)
                    )
            else:
                tag_open = f"{indent}<{tag_name}"

            # Categorize children: visual within this file vs imported external file roots
            visual_same_file = [
                c for c in item.child_xui_items if c.source_file == fname
            ]
            imported_roots = [
                c
                for c in item.child_xui_items
                if getattr(c, 'is_imported_root', False)
            ]

            has_children = (
                bool(visual_same_file)
                or bool(item.non_visual_children)
                or bool(item.inner_text)
            )

            # Generate self-closing tags for leaf nodes; full block tags for parents
            if not has_children:
                lines.extend((tag_open + " />").split('\n'))
                end_line = len(lines) - 1
            else:
                lines.extend((tag_open + ">").split('\n'))

                # Write inner text payload if present
                if item.inner_text:
                    lines.append(f"{indent}    {item.inner_text}")

                # Serialize non-visual data children (e.g., event bindings, timers)
                for nv_child in item.non_visual_children:
                    nv_tag, nv_attrs = nv_child['tag'], nv_child['attributes']
                    attr_strs = [f'{k}="{v}"' for k, v in sorted(nv_attrs.items())]
                    attr_str = ""
                    if attr_strs:
                        if len(attr_strs) <= 2:
                            attr_str = " " + " ".join(attr_strs)
                        else:
                            attr_indent = indent + "      "
                            attr_str = (
                                f"\n{attr_indent}" + f"\n{attr_indent}".join(attr_strs)
                            )
                    lines.extend((f"{indent}    <{nv_tag}{attr_str} />").split('\n'))

                # Recursively compile child elements belonging to the same file
                for child in visual_same_file:
                    _build_lines(child, indent_lvl + 1)

                lines.append(f"{indent}</{tag_name}>")
                end_line = len(lines) - 1

            # Track line boundaries for active selections in the code editor
            if item == selected_item:
                selections['selected'].append((start_line, end_line))

            # Run validation checks and track error/warning line ranges
            errors, warnings = item.validate()
            if errors:
                selections['errors'].append((start_line, end_line, errors))
            if warnings:
                selections['warnings'].append((start_line, end_line, warnings))

            # Cascade build to imported files, resetting indentation to root level (0)
            for imp_child in imported_roots:
                _build_lines(imp_child, 0)

        # Initiate compilation from the provided root element
        if root_item:
            init_file(getattr(root_item, 'source_file', 'layout.xml'))
            _build_lines(root_item, 0)

        # Assemble final output dictionary mapping filenames to compiled strings and metadata
        results = {}
        for k, v in files.items():
            results[k] = ("\n".join(v['lines']), v['selections'])
        return results