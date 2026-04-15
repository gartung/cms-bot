#! /usr/bin/env python3

import sys
import json
import os

threshold = 5000.0
error_threshold = 20000.0

BEGIN_RUN_KEYS = ["global begin run", "stream begin run"]
BEGIN_LUMI_KEYS = [
    "global begin luminosity block",
    "stream begin luminosity block",
]
CONSTRUCTION_KEYS = ["construction"]
EVENT_KEYS = ["event"]
EVENT_SETUP_KEYS = ["event setup"]
TOTAL_KEYS = [
    *CONSTRUCTION_KEYS,
    *EVENT_KEYS,
    *EVENT_SETUP_KEYS,
    *BEGIN_LUMI_KEYS,
    *BEGIN_RUN_KEYS,
    *BEGIN_LUMI_KEYS,
]

METRICS_KEYS = ["added", "nAlloc", "nDealloc", "maxTemp", "max1Alloc"]


def module_key(module):
    return "%s|%s|%s" % (module.get("label", ""), module.get("type", ""), module.get("record", ""))


def numeric_value(data, key, default="N/A"):
    value = data.get(key, default)
    return value if isinstance(value, (int, float)) else default


def sum_numeric_values(data, keys, default="N/A"):
    values = [data.get(key, default) for key in keys]
    return sum(values) if all(isinstance(value, (int, float)) for value in values) else default


def sum_with_prefix_suffix(data, metric_keys, prefix="added", suffix="", default="N/A"):
    return sum_numeric_values(
        data, ["%s %s %s" % (prefix, metric, suffix) for metric in metric_keys], default
    )


def format_metric(value):
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def append_triplet_cell(summary_lines, ib, pr, diff, attrs='align="right"'):
    summary_lines.append(
        "<td %s>%s<br>%s<br>%s</td>"
        % (attrs, format_metric(ib), format_metric(pr), format_metric(diff))
    )


def added_total_color(diff_value):
    if not isinstance(diff_value, (int, float)):
        return ""
    if diff_value > error_threshold:
        return 'bgcolor="red"'
    if diff_value > threshold:
        return 'bgcolor="orange"'
    if diff_value < -1.0 * error_threshold:
        return 'bgcolor="green"'
    if diff_value < -1.0 * threshold:
        return 'bgcolor="cyan"'
    return ""


def is_valid_module_key(key):
    return key != "None|None|None" and key != "||"


def transitions_diff_value(transitions_ib, transitions_pr):
    if isinstance(transitions_ib, (int, float)) and isinstance(transitions_pr, (int, float)):
        return transitions_ib - transitions_pr
    if not isinstance(transitions_ib, (int, float)) and isinstance(transitions_pr, (int, float)):
        return transitions_pr - 0
    if isinstance(transitions_ib, (int, float)) and not isinstance(transitions_pr, (int, float)):
        return 0 - transitions_ib
    return "N/A"


def update_added_totals(datamapres):
    for module in datamapres.values():
        key = module_key(module)
        if not is_valid_module_key(key):
            continue
        for metric in METRICS_KEYS:
            module[f"{metric} total PR"] = sum_with_prefix_suffix(
                module, TOTAL_KEYS, prefix=metric, suffix="PR"
            )
            module[f"{metric} total IB"] = sum_with_prefix_suffix(
                module, TOTAL_KEYS, prefix=metric, suffix="IB"
            )
            module[f"{metric} total diff"] = sum_with_prefix_suffix(
                module, TOTAL_KEYS, prefix=metric, suffix="diff"
            )


def build_summary_header(ibdata, prdata, results):
    return [
        "<html>",
        "<head><style>",
        "table, th, td {border: 1px solid black;}</style>",
        "<style> th, td {padding: 15px;}</style></head>",
        "<body><h3>ModuleAllocMonitor Resources Difference</h3><table>",
        '</table><table><tr><td bgcolor="orange">',
        "warn threshold %0.2f kB" % threshold,
        '</td></tr><tr><td bgcolor="red">',
        "error threshold %0.2f kB" % error_threshold,
        '</td></tr><tr><td bgcolor="green">',
        "warn threshold -%0.2f kB" % threshold,
        '</td></tr><tr><td bgcolor="cyan">',
        "warn threshold -%0.2f kB" % error_threshold,
        "</td></tr>",
        "<tr><td>metric:<BR>&lt;baseline&gt;<BR>&lt;pull request&gt;<BR>&lt;PR - baseline&gt; </td>",
        "</tr></table>",
        "<table>",
        '<tr><td align="center">Type<BR>Label</td>',
        '<td align="center">added construction</td>',
        '<td align="center">added begin run</td>',
        '<td align="center">added begin luminosity block</td>',
        '<td align="center">added event</td>',
        '<td align="center">added event setup</td>',
        '<td align="center">nAlloc construction</td>',
        '<td align="center">nAlloc begin run</td>',
        '<td align="center">nAlloc begin luminosity block</td>',
        '<td align="center">nAlloc event</td>',
        '<td align="center">nAlloc event setup</td>',
        "</tr>",
        "<td>%s<BR>%s</td>" % (prdata["total"]["type"], prdata["total"]["label"]),
        '<td align="right">%0.2f<br>%0.2f<br>%0.2f</td>'
        % (
            ibdata["total"]["added construction"],
            prdata["total"]["added construction"],
            results["total"]["added construction diff"],
        ),
        '<td align="right">%0.2f<br>%0.2f<br>%0.2f</td>'
        % (
            ibdata["total"]["added global begin run"] + ibdata["total"]["added stream begin run"],
            prdata["total"]["added global begin run"] + prdata["total"]["added stream begin run"],
            results["total"]["added global begin run diff"]
            + results["total"]["added stream begin run diff"],
        ),
        '<td align="right">%0.2f<br>%0.2f<br>%0.2f</td>'
        % (
            ibdata["total"]["added global begin luminosity block"]
            + ibdata["total"]["added stream begin luminosity block"],
            prdata["total"]["added global begin luminosity block"]
            + prdata["total"]["added stream begin luminosity block"],
            results["total"]["added global begin luminosity block diff"]
            + results["total"]["added stream begin luminosity block diff"],
        ),
        '<td align="right">%0.2f<br>%0.2f<br>%0.2f</td>'
        % (
            ibdata["total"]["added event"],
            prdata["total"]["added event"],
            results["total"]["added event diff"],
        ),
        '<td align="right">%0.2f<br>%0.2f<br>%0.2f</td>'
        % (
            ibdata["total"]["added event setup"],
            prdata["total"]["added event setup"],
            results["total"]["added event setup diff"],
        ),
        '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
        % (
            ibdata["total"]["nAlloc construction"],
            prdata["total"]["nAlloc construction"],
            results["total"]["nAlloc construction diff"],
        ),
        '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
        % (
            ibdata["total"]["nAlloc global begin run"]
            + ibdata["total"]["nAlloc stream begin run"],
            prdata["total"]["nAlloc global begin run"]
            + prdata["total"]["nAlloc stream begin run"],
            results["total"]["nAlloc global begin run diff"]
            + results["total"]["nAlloc stream begin run diff"],
        ),
        '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
        % (
            ibdata["total"]["nAlloc global begin luminosity block"]
            + ibdata["total"]["nAlloc stream begin luminosity block"],
            prdata["total"]["nAlloc global begin luminosity block"]
            + prdata["total"]["nAlloc stream begin luminosity block"],
            results["total"]["nAlloc global begin luminosity block diff"]
            + results["total"]["nAlloc stream begin luminosity block diff"],
        ),
        '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
        % (
            ibdata["total"]["nAlloc event"],
            prdata["total"]["nAlloc event"],
            results["total"]["nAlloc event diff"],
        ),
        '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
        % (
            ibdata["total"]["nAlloc event setup"],
            prdata["total"]["nAlloc event setup"],
            results["total"]["nAlloc event setup diff"],
        ),
        "</tr></table>",
        '<table><tr><td align="center">Module label<BR>Module type<BR>Module record</td>',
        '<td align="center">added construction</td>',
        '<td align="center">added begin run</td>',
        '<td align="center">added begin luminosity block</td>',
        '<td align="center">added event</td>',
        '<td align="center">added event setup</td>',
        '<td align="center">added total</td>',
        '<td align="center">nAlloc construction</td>',
        '<td align="center">nAlloc begin run</td>',
        '<td align="center">nAlloc begin luminosity block</td>',
        '<td align="center">nAlloc event</td>',
        '<td align="center">nAlloc event setup</td>',
        '<td align="center">nAlloc total</td>',
        '<td align="center">nDealloc construction</td>',
        '<td align="center">nDealloc begin run</td>',
        '<td align="center">nDealloc begin luminosity block</td>',
        '<td align="center">nDealloc event</td>',
        '<td align="center">nDealloc event setup</td>',
        '<td align="center">nDealloc total</td>',
        '<td align="center">maxTemp construction</td>',
        '<td align="center">maxTemp begin run</td>',
        '<td align="center">maxTemp begin luminosity block</td>',
        '<td align="center">maxTemp event</td>',
        '<td align="center">maxTemp event setup</td>',
        '<td align="center">maxTemp total</td>',
        '<td align="center">max1Alloc construction</td>',
        '<td align="center">max1Alloc begin run</td>',
        '<td align="center">max1Alloc begin luminosity block</td>',
        '<td align="center">max1Alloc event</td>',
        '<td align="center">max1Alloc event setup</td>',
        '<td align="center">max1Alloc total</td>',
        '<td align="center">transitions</td>',
        "</tr>",
    ]


def append_module_columns_prefix(summary_lines, moduleres, prefix):
    addedtotaldiff = numeric_value(moduleres, "added total diff", float("-inf"))
    color = added_total_color(addedtotaldiff)
    cell_attrs = 'align="right"'
    if color:
        cell_attrs += " " + color

    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, CONSTRUCTION_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, CONSTRUCTION_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, CONSTRUCTION_KEYS, prefix=prefix, suffix="diff"),
    )
    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, BEGIN_RUN_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, BEGIN_RUN_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, BEGIN_RUN_KEYS, prefix=prefix, suffix="diff"),
    )
    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, BEGIN_LUMI_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, BEGIN_LUMI_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, BEGIN_LUMI_KEYS, prefix=prefix, suffix="diff"),
    )
    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, EVENT_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, EVENT_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, EVENT_KEYS, prefix=prefix, suffix="diff"),
    )
    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, EVENT_SETUP_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, EVENT_SETUP_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, EVENT_SETUP_KEYS, prefix=prefix, suffix="diff"),
    )
    append_triplet_cell(
        summary_lines,
        sum_with_prefix_suffix(moduleres, TOTAL_KEYS, prefix=prefix, suffix="IB"),
        sum_with_prefix_suffix(moduleres, TOTAL_KEYS, prefix=prefix, suffix="PR"),
        sum_with_prefix_suffix(moduleres, TOTAL_KEYS, prefix=prefix, suffix="diff"),
        attrs=cell_attrs,
    )


def append_module_rows(summary_lines, moduleib, modulepr, moduleres):
    summary_lines += [
        "<tr>",
        '<td align="center">%s<BR>%s<BR> %s</td>'
        % (moduleres.get("label", ""), moduleres.get("type", ""), moduleres.get("record", "")),
    ]
    for metric in METRICS_KEYS:
        append_module_columns_prefix(summary_lines, moduleres, metric)

    transitions_ib = numeric_value(moduleib, "transitions")
    transitions_pr = numeric_value(modulepr, "transitions")
    transitions_diff = transitions_diff_value(transitions_ib, transitions_pr)
    append_triplet_cell(summary_lines, transitions_ib, transitions_pr, transitions_diff)


def append_sorted_module_rows(summary_lines, datamapib, datamappr, datamapres):
    for item in sorted(
        datamapres.items(),
        key=lambda x: numeric_value(x[1], "added total diff", float("-inf")),
        reverse=True,
    ):
        key = module_key(item[1])
        if not is_valid_module_key(key):
            continue
        moduleib = datamapib.get(key, {})
        modulepr = datamappr.get(key, {})
        moduleres = datamapres.get(key, {})
        append_module_rows(summary_lines, moduleib, modulepr, moduleres)


def build_summary_lines(ibdata, prdata, results, datamapib, datamappr, datamapres):
    summary_lines = build_summary_header(ibdata, prdata, results)
    update_added_totals(datamapres)
    append_sorted_module_rows(summary_lines, datamapib, datamappr, datamapres)
    summary_lines += ["</body></html>"]
    return summary_lines


def diff_from(metrics, data, dest, res):
    for metric in metrics:
        ibkey = "%s IB" % metric
        res[ibkey] = data.get(metric, "N/A")
        prkey = "%s PR" % metric
        res[prkey] = dest.get(metric, "N/A")
        if res[ibkey] == "N/A" or res[prkey] == "N/A":
            if res[prkey] != "N/A":
                res[metric + " diff"] = res[prkey] - 0
            elif res[ibkey] != "N/A":
                res[metric + " diff"] = 0 - res[ibkey]
        else:
            dmetric = dest.get(metric) - data.get(metric)
            res[metric + " diff"] = dmetric


if len(sys.argv) == 1:
    print("""Usage: resources-diff.py IB_FILE PR_FILE
Diff the content of two "resources.json" files and print the result to standard output.""")
    sys.exit(1)

with open(sys.argv[1]) as f:
    ibdata = json.load(f)

metrics = []
for resource in ibdata["resources"]:
    if "name" in resource:
        metrics.append(resource["name"])
    else:
        for key in resource:
            metrics.append(key)

datamapib = {module_key(module): module for module in ibdata["modules"]}

datacumulsib = {}
for module in ibdata["modules"]:
    datacumul = datacumulsib.get(module["type"])
    if datacumul:
        datacumul["count"] += 1
        for metric in metrics:
            datacumul[metric] += module[metric]
    else:
        datacumul = {}
        datacumul["count"] = 1
        for metric in metrics:
            datacumul[metric] = module[metric]
        datacumulsib[module["type"]] = datacumul

with open(sys.argv[2]) as f:
    prdata = json.load(f)
if ibdata["resources"] != prdata["resources"]:
    print("Error: input files describe different metrics")
    sys.exit(1)

datamappr = {module_key(module): module for module in prdata["modules"]}


if ibdata["total"]["label"] != prdata["total"]["label"]:
    print("Warning: input files describe different process names")

results = {}
results["resources"] = []
for resource in prdata["resources"]:
    resourcediff = resource.copy()
    resourceib = resource.copy()
    resourcepr = resource.copy()
    for k, v in resource.items():
        resourcediff[k] = "%s diff" % v
        resourceib[k] = "%s IB" % v
        resourcepr[k] = "%s PR" % v
    results["resources"].append(resourcediff)
    results["resources"].append(resourceib)
    results["resources"].append(resourcepr)

results["total"] = {}
results["total"]["type"] = prdata["total"]["type"]
results["total"]["label"] = prdata["total"]["label"]

diff_from(metrics, ibdata["total"], prdata["total"], results["total"])

results["modules"] = []
keys = set()
for module in prdata["modules"]:
    keys.add(module_key(module))
for module in ibdata["modules"]:
    keys.add(module_key(module))
for key in sorted(keys):
    result = {}
    if key in datamapib and key not in datamappr:
        result["type"] = datamapib.get(key).get("type")
        result["label"] = datamapib.get(key).get("label")
        result["record"] = datamapib.get(key).get("record")
        diff_from(metrics, datamapib.get(key, {}), {}, result)
    elif key in datamappr and key not in datamapib:
        result["type"] = datamappr.get(key).get("type")
        result["label"] = datamappr.get(key).get("label")
        result["record"] = datamappr.get(key).get("record")
        diff_from(metrics, {}, datamappr.get(key, {}), result)
    else:
        result["type"] = datamappr.get(key).get("type")
        result["label"] = datamappr.get(key).get("label")
        result["record"] = datamappr.get(key).get("record")
        diff_from(metrics, datamapib.get(key, {}), datamappr.get(key, {}), result)
    results["modules"].append(result)

datamapres = {}
for module in results["modules"]:
    datamapres[module_key(module)] = module


summaryLines = build_summary_lines(ibdata, prdata, results, datamapib, datamappr, datamapres)
dumpfile = (
    os.path.dirname(os.path.realpath(sys.argv[2]))
    + "/diff-"
    + os.path.basename(os.path.realpath(sys.argv[2]))
    + ".json"
)
with open(dumpfile, "w") as f:
    json.dump(results, f, indent=2)

summaryFile = (
    os.path.dirname(os.path.realpath(sys.argv[2]))
    + "/diff-"
    + os.path.basename(os.path.realpath(sys.argv[2]))
    + ".html"
)
with open(summaryFile, "w") as g:
    for summaryLine in summaryLines:
        print(summaryLine, file=g)
