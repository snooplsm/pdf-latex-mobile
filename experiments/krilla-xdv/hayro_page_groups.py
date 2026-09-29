"""Opt-in xdvipdfmx compatibility for imported PDF page groups.

The original mobile backend omits source page groups. Hayro's upstream default
isolates imports. Keep that default unless this explicit compatibility feature
is enabled; omitting groups can change source-PDF transparency semantics.
"""
OLD = '    // Latex seems to isolate all embedded PDFs which makes sense, so we also\n    // do the same. See also https://github.com/typst/typst/issues/7269.\n    let mut group = x_object.group();\n    group.transparency().isolated(true);\n    write_xobject_group_cs(&mut group);\n    group.finish();'
NEW = """    // Match the existing xdvipdfmx importer, which omits page groups.
    // Retain upstream Hayro behavior for callers not requesting compatibility.
    if !cfg!(feature = "xdvipdfmx-compatibility") {
""" + "\n".join("    " + line for line in OLD.splitlines()) + "\n    }"

def patch(body):
    assert body.count(OLD) == 1, 'Upstream group implementation changed'
    return body.replace(OLD, NEW)
