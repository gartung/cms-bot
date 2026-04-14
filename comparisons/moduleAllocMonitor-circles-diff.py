#! /usr/bin/env python3

import sys
import json
import os
import math

threshold = 5000.0
error_threshold = 20000.0


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

datamapib = {
    module["label"] + "|" + module["type"] + "|" + module["record"]: module
    for module in ibdata["modules"]
}

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

datamappr = {
    module["label"] + "|" + module["type"] + "|" + module["record"]: module
    for module in prdata["modules"]
}


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
    key = module["label"] + "|" + module["type"] + "|" + module["record"]
    keys.add(key)
for module in ibdata["modules"]:
    key = module["label"] + "|" + module["type"] + "|" + module["record"]
    keys.add(key)
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
    datamapres[
        "%s|%s|%s" % (module.get("label", ""), module.get("type", ""), module.get("record", ""))
    ] = module


summaryLines = []
summaryLines += [
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
        ibdata["total"]["nAlloc global begin run"] + ibdata["total"]["nAlloc stream begin run"],
        prdata["total"]["nAlloc global begin run"] + prdata["total"]["nAlloc stream begin run"],
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
    '<td align="center">added construction (kB)</td>',
    '<td align="center">added begin run (kB)</td>',
    '<td align="center">added begin luminosity block (kB)</td>',
    '<td align="center">added event (kB)</td>',
    '<td align="center">added event setup (kB)</td>',
    '<td align="center">added total (kB)</td>',
    '<td align="center">nAlloc construction</td>',
    '<td align="center">nAlloc begin run</td>',
    '<td align="center">nAlloc begin luminosity block</td>',
    '<td align="center">nAlloc event</td>',
    '<td align="center">nAlloc event setup</td>',
    '<td align="center">nAlloc total</td>',
    '<td align="center">transitions</td>',
    "</tr>",
]

for item in datamapres.items():
    key = "%s|%s|%s" % (
        item[1].get("label", ""),
        item[1].get("type", ""),
        item[1].get("record", ""),
    )
    if not key == "None|None|None" and not key == "||":
        moduleib = datamapib.get(key, {})
        modulepr = datamappr.get(key, {})
        moduleres = datamapres.get(key, {})
        added_total_pr = (
            (
                moduleres.get("added event setup PR", 0)
                + moduleres.get("added event PR", 0)
                + moduleres.get("added construction PR", 0)
                + moduleres.get("added global begin run PR", 0)
                + moduleres.get("added stream begin run PR", 0)
                + moduleres.get("added global begin luminosity block PR", 0)
                + moduleres.get("added stream begin luminosity block PR", 0)
            )
            if isinstance(moduleres.get("added event setup PR", 0), (int, float))
            and isinstance(moduleres.get("added event PR", 0), (int, float))
            and isinstance(moduleres.get("added construction PR", 0), (int, float))
            and isinstance(moduleres.get("added global begin run PR", 0), (int, float))
            and isinstance(moduleres.get("added stream begin run PR", 0), (int, float))
            and isinstance(
                moduleres.get("added global begin luminosity block PR", 0), (int, float)
            )
            and isinstance(
                moduleres.get("added stream begin luminosity block PR", 0), (int, float)
            )
            else "N/A"
        )
        moduleres["added total PR"] = added_total_pr
        added_total_ib = (
            (
                moduleres.get("added event setup IB", 0)
                + moduleres.get("added event IB", 0)
                + moduleres.get("added construction IB", 0)
                + moduleres.get("added global begin run IB", 0)
                + moduleres.get("added stream begin run IB", 0)
                + moduleres.get("added global begin luminosity block IB", 0)
                + moduleres.get("added stream begin luminosity block IB", 0)
            )
            if isinstance(moduleres.get("added event setup IB", 0), (int, float))
            and isinstance(moduleres.get("added event IB", 0), (int, float))
            and isinstance(moduleres.get("added construction IB", 0), (int, float))
            and isinstance(moduleres.get("added global begin run IB", 0), (int, float))
            and isinstance(moduleres.get("added stream begin run IB", 0), (int, float))
            and isinstance(
                moduleres.get("added global begin luminosity block IB", 0), (int, float)
            )
            and isinstance(
                moduleres.get("added stream begin luminosity block IB", 0), (int, float)
            )
            else "N/A"
        )
        moduleres["added total IB"] = added_total_ib
        added_total_diff = (
            (
                moduleres.get("added event setup diff", 0)
                + moduleres.get("added event diff", 0)
                + moduleres.get("added construction diff", 0)
                + moduleres.get("added global begin run diff", 0)
                + moduleres.get("added stream begin run diff", 0)
                + moduleres.get("added global begin luminosity block diff", 0)
                + moduleres.get("added stream begin luminosity block diff", 0)
            )
            if isinstance(moduleres.get("added event setup diff", 0), (int, float))
            and isinstance(moduleres.get("added event diff", 0), (int, float))
            and isinstance(moduleres.get("added construction diff", 0), (int, float))
            and isinstance(moduleres.get("added global begin run diff", 0), (int, float))
            and isinstance(moduleres.get("added stream begin run diff", 0), (int, float))
            and isinstance(
                moduleres.get("added global begin luminosity block diff", 0), (int, float)
            )
            and isinstance(
                moduleres.get("added stream begin luminosity block diff", 0), (int, float)
            )
            else "N/A"
        )
        moduleres["added total diff"] = added_total_diff
dumpfile = (
    os.path.dirname(os.path.realpath(sys.argv[2]))
    + "/diff-"
    + os.path.basename(os.path.realpath(sys.argv[2]))
    + ".json"
)
with open(dumpfile, "w") as f:
    json.dump(results, f, indent=2)

for item in sorted(
    datamapres.items(),
    key=lambda x: (
        x[1].get("added total diff", float("-inf"))
        if isinstance(x[1].get("added total diff", float("-inf")), (int, float))
        else float("-inf")
    ),
    reverse=True,
):
    key = "%s|%s|%s" % (
        item[1].get("label", ""),
        item[1].get("type", ""),
        item[1].get("record", ""),
    )
    if not key == "None|None|None" and not key == "||":
        moduleib = datamapib.get(key, {})
        modulepr = datamappr.get(key, {})
        moduleres = datamapres.get(key, {})
        cellString = '<td align="right" '
        color = ""
        addedtotaldiff = (
            moduleres.get("added total diff", float("-inf"))
            if isinstance(moduleres.get("added total diff", float("-inf")), (int, float))
            else float("-inf")
        )
        if addedtotaldiff > threshold:
            color = 'bgcolor="orange"'
        if addedtotaldiff > error_threshold:
            color = 'bgcolor="red"'
        if addedtotaldiff < -1.0 * threshold:
            color = 'bgcolor="cyan"'
        if addedtotaldiff < -1.0 * error_threshold:
            color = 'bgcolor="green"'
        cellString += color
        cellString += ">"
        summaryLines += [
            "<tr>",
            '<td align="center">%s<BR>%s<BR> %s</td>'
            % (moduleres.get("label", ""), moduleres.get("type", ""), moduleres.get("record", "")),
        ]
        added_construction_ib = (
            moduleres.get("added construction IB", "N/A")
            if isinstance(moduleres.get("added construction IB", "N/A"), (int, float))
            else "N/A"
        )
        added_construction_pr = (
            moduleres.get("added construction PR", "N/A")
            if isinstance(moduleres.get("added construction PR", "N/A"), (int, float))
            else "N/A"
        )
        added_construction_diff = (
            moduleres.get("added construction diff", "N/A")
            if isinstance(moduleres.get("added construction diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{added_construction_ib:{".2f" if isinstance(added_construction_ib, (float)) else ""}}'
            + "<br>"
            + f'{added_construction_pr:{".2f" if isinstance(added_construction_pr, (float)) else ""}}'
            + "<br>"
            + f'{added_construction_diff:{".2f" if isinstance(added_construction_diff, (float)) else ""}}'
            + "</td>"
        ]
        added_begin_run_ib = (
            (
                moduleib.get("added global begin run", "N/A")
                + moduleib.get("added stream begin run", "N/A")
            )
            if isinstance(moduleib.get("added global begin run", "N/A"), (int, float))
            and isinstance(moduleib.get("added stream begin run", "N/A"), (int, float))
            else "N/A"
        )
        added_begin_run_pr = (
            (
                modulepr.get("added global begin run", "N/A")
                + modulepr.get("added stream begin run", "N/A")
            )
            if isinstance(modulepr.get("added global begin run", "N/A"), (int, float))
            and isinstance(modulepr.get("added stream begin run", "N/A"), (int, float))
            else "N/A"
        )
        added_begin_run_diff = (
            (
                moduleres.get("added global begin run diff", "N/A")
                + moduleres.get("added stream begin run diff", "N/A")
            )
            if isinstance(moduleres.get("added global begin run diff", "N/A"), (int, float))
            and isinstance(moduleres.get("added stream begin run diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            (
                '<td align="right">'
                + f'{added_begin_run_ib:{".2f" if isinstance(added_begin_run_ib, (float)) else ""}}'
                + "<br>"
                + f'{added_begin_run_pr:{".2f" if isinstance(added_begin_run_pr, (float)) else ""}}'
                + "<br>"
                + f'{added_begin_run_diff:{".2f" if isinstance(added_begin_run_diff, (float)) else ""}}'
                + "</td>"
            )
        ]
        added_luminosity_block_ib = (
            (
                moduleib.get("added global begin luminosity block", "N/A")
                + moduleib.get("added stream begin luminosity block", "N/A")
            )
            if isinstance(moduleib.get("added global begin luminosity block", "N/A"), (int, float))
            and isinstance(
                moduleib.get("added stream begin luminosity block", "N/A"), (int, float)
            )
            else "N/A"
        )
        added_luminosity_block_pr = (
            (
                modulepr.get("added global begin luminosity block", "N/A")
                + modulepr.get("added stream begin luminosity block", "N/A")
            )
            if isinstance(modulepr.get("added global begin luminosity block", "N/A"), (int, float))
            and isinstance(
                modulepr.get("added stream begin luminosity block", "N/A"), (int, float)
            )
            else "N/A"
        )
        added_luminosity_block_diff = (
            (
                moduleres.get("added global begin luminosity block diff", "N/A")
                + moduleres.get("added stream begin luminosity block diff", "N/A")
            )
            if isinstance(
                moduleres.get("added global begin luminosity block diff", "N/A"), (int, float)
            )
            and isinstance(
                moduleres.get("added stream begin luminosity block diff", "N/A"), (int, float)
            )
            else "N/A"
        )
        summaryLines += [
            (
                '<td align="right">'
                + f'{added_luminosity_block_ib:{".2f" if isinstance(added_luminosity_block_ib, (float)) else ""}}'
                + "<br>"
                + f'{added_luminosity_block_pr:{".2f" if isinstance(added_luminosity_block_pr, (float)) else ""}}'
                + "<br>"
                + f'{added_luminosity_block_diff:{".2f" if isinstance(added_luminosity_block_diff, (float)) else ""}}'
                + "</td>"
            )
        ]
        added_event_ib = (
            moduleib.get("added event", "N/A")
            if isinstance(moduleib.get("added event", "N/A"), (int, float))
            else "N/A"
        )
        added_event_pr = (
            modulepr.get("added event", "N/A")
            if isinstance(modulepr.get("added event", "N/A"), (int, float))
            else "N/A"
        )
        added_event_diff = (
            moduleres.get("added event diff", "N/A")
            if isinstance(moduleres.get("added event diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            (
                '<td align="right">'
                + f'{added_event_ib:{".2f" if isinstance(added_event_ib, (float)) else ""}}'
                + "<br>"
                + f'{added_event_pr:{".2f" if isinstance(added_event_pr, (float)) else ""}}'
                + "<br>"
                + f'{added_event_diff:{".2f" if isinstance(added_event_diff, (float)) else ""}}'
                + "</td>"
            )
        ]
        added_event_setup_ib = (
            moduleib.get("added event setup", "N/A")
            if isinstance(moduleib.get("added event setup", "N/A"), (int, float))
            else "N/A"
        )
        added_event_setup_pr = (
            modulepr.get("added event setup", "N/A")
            if isinstance(modulepr.get("added event setup", "N/A"), (int, float))
            else "N/A"
        )
        added_event_setup_diff = (
            moduleres.get("added event setup diff", "N/A")
            if isinstance(moduleres.get("added event setup diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            (
                '<td align="right">'
                + f'{added_event_setup_ib:{".2f" if isinstance(added_event_setup_ib, (float)) else ""}}'
                + "<br>"
                + f'{added_event_setup_pr:{".2f" if isinstance(added_event_setup_pr, (float)) else ""}}'
                + "<br>"
                + f'{added_event_setup_diff:{".2f" if isinstance(added_event_setup_diff, (float)) else ""}}'
                + "</td>"
            )
        ]
        added_total_ib = (
            (
                moduleib.get("added event setup", "N/A")
                + moduleib.get("added event", "N/A")
                + moduleib.get("added construction", "N/A")
                + moduleib.get("added global begin run", "N/A")
                + moduleib.get("added stream begin run", "N/A")
                + moduleib.get("added global begin luminosity block", "N/A")
                + moduleib.get("added stream begin luminosity block", "N/A")
            )
            if isinstance(moduleib.get("added event setup", "N/A"), (int, float))
            and isinstance(moduleib.get("added event", "N/A"), (int, float))
            and isinstance(moduleib.get("added construction", "N/A"), (int, float))
            and isinstance(moduleib.get("added global begin run", "N/A"), (int, float))
            and isinstance(moduleib.get("added stream begin run", "N/A"), (int, float))
            and isinstance(
                moduleib.get("added global begin luminosity block", "N/A"), (int, float)
            )
            and isinstance(
                moduleib.get("added stream begin luminosity block", "N/A"), (int, float)
            )
            else "N/A"
        )
        added_total_pr = (
            (
                modulepr.get("added event setup", "N/A")
                + modulepr.get("added event", "N/A")
                + modulepr.get("added construction", "N/A")
                + modulepr.get("added global begin run", "N/A")
                + modulepr.get("added stream begin run", "N/A")
                + modulepr.get("added global begin luminosity block", "N/A")
                + modulepr.get("added stream begin luminosity block", "N/A")
            )
            if isinstance(modulepr.get("added event setup", "N/A"), (int, float))
            and isinstance(modulepr.get("added event", "N/A"), (int, float))
            and isinstance(modulepr.get("added construction", "N/A"), (int, float))
            and isinstance(modulepr.get("added global begin run", "N/A"), (int, float))
            and isinstance(modulepr.get("added stream begin run", "N/A"), (int, float))
            and isinstance(
                modulepr.get("added global begin luminosity block", "N/A"), (int, float)
            )
            and isinstance(
                modulepr.get("added stream begin luminosity block", "N/A"), (int, float)
            )
            else "N/A"
        )
        added_total_diff = (
            (
                moduleres.get("added event setup diff", "N/A")
                + moduleres.get("added event diff", "N/A")
                + moduleres.get("added construction diff", "N/A")
                + moduleres.get("added global begin run diff", "N/A")
                + moduleres.get("added stream begin run diff", "N/A")
                + moduleres.get("added global begin luminosity block diff", "N/A")
                + moduleres.get("added stream begin luminosity block diff", "N/A")
            )
            if isinstance(moduleres.get("added event setup diff", "N/A"), (int, float))
            and isinstance(moduleres.get("added event diff", "N/A"), (int, float))
            and isinstance(moduleres.get("added construction diff", "N/A"), (int, float))
            and isinstance(moduleres.get("added global begin run diff", "N/A"), (int, float))
            and isinstance(moduleres.get("added stream begin run diff", "N/A"), (int, float))
            and isinstance(
                moduleres.get("added global begin luminosity block diff", "N/A"), (int, float)
            )
            and isinstance(
                moduleres.get("added stream begin luminosity block diff", "N/A"), (int, float)
            )
            else "N/A"
        )
        summaryLines += [
            (
                cellString
                + f"{added_total_ib:{'.2f' if isinstance(added_total_ib, (float)) else ''}}"
                + "<br>"
                + f"{added_total_pr:{'.2f' if isinstance(added_total_pr, (float)) else ''}}"
                + "<br>"
                + f"{added_total_diff:{'.2f' if isinstance(added_total_diff, (float)) else ''}}"
                + "</td>"
            )
        ]
        nAlloc_construction_ib = (
            moduleres.get("nAlloc construction IB", "N/A")
            if isinstance(moduleres.get("nAlloc construction IB", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_construction_pr = (
            moduleres.get("nAlloc construction PR", "N/A")
            if isinstance(moduleres.get("nAlloc construction PR", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_construction_diff = (
            moduleres.get("nAlloc construction diff", "N/A")
            if isinstance(moduleres.get("nAlloc construction diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            f'<td align="right">{nAlloc_construction_ib:{".2f" if isinstance(nAlloc_construction_ib, (float)) else ""}}'
            + f'<br>{nAlloc_construction_pr:{".2f" if isinstance(nAlloc_construction_pr, (float)) else ""}}'
            + f'<br>{nAlloc_construction_diff:{".2f" if isinstance(nAlloc_construction_diff, (float)) else ""}}</td>'
        ]
        nAlloc_begin_run_ib = (
            (
                moduleres.get("nAlloc global begin run IB", "N/A")
                + moduleres.get("nAlloc stream begin run IB", "N/A")
            )
            if isinstance(moduleres.get("nAlloc global begin run IB", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc stream begin run IB", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_begin_run_pr = (
            (
                moduleres.get("nAlloc global begin run PR", "N/A")
                + moduleres.get("nAlloc stream begin run PR", "N/A")
            )
            if isinstance(moduleres.get("nAlloc global begin run PR", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc stream begin run PR", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_begin_run_diff = (
            (
                moduleres.get("nAlloc global begin run diff", "N/A")
                + moduleres.get("nAlloc stream begin run diff", "N/A")
            )
            if isinstance(moduleres.get("nAlloc global begin run diff", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc stream begin run diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{nAlloc_begin_run_ib:{".2f" if isinstance(nAlloc_begin_run_ib, (float)) else ""}}'
            + f'<br>{nAlloc_begin_run_pr:{".2f" if isinstance(nAlloc_begin_run_pr, (float)) else ""}}'
            + f'<br>{nAlloc_begin_run_diff:{".2f" if isinstance(nAlloc_begin_run_diff, (float)) else ""}}</td>'
        ]
        nAlloc_begin_luminosity_block_ib = (
            (
                moduleres.get("nAlloc global begin luminosity block IB", "N/A")
                + moduleres.get("nAlloc stream begin luminosity block IB", "N/A")
            )
            if isinstance(
                moduleres.get("nAlloc global begin luminosity block IB", "N/A"), (int, float)
            )
            and isinstance(
                moduleres.get("nAlloc stream begin luminosity block IB", "N/A"), (int, float)
            )
            else "N/A"
        )
        nAlloc_begin_luminosity_block_pr = (
            (
                moduleres.get("nAlloc global begin luminosity block PR", "N/A")
                + moduleres.get("nAlloc stream begin luminosity block PR", "N/A")
            )
            if isinstance(
                moduleres.get("nAlloc global begin luminosity block PR", "N/A"), (int, float)
            )
            and isinstance(
                moduleres.get("nAlloc stream begin luminosity block PR", "N/A"), (int, float)
            )
            else "N/A"
        )
        nAlloc_begin_luminosity_block_diff = (
            (
                moduleres.get("nAlloc global begin luminosity block diff", "N/A")
                + moduleres.get("nAlloc stream begin luminosity block diff", "N/A")
            )
            if isinstance(
                moduleres.get("nAlloc global begin luminosity block diff", "N/A"), (int, float)
            )
            and isinstance(
                moduleres.get("nAlloc stream begin luminosity block diff", "N/A"), (int, float)
            )
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{nAlloc_begin_luminosity_block_ib:{".2f" if isinstance(nAlloc_begin_luminosity_block_ib, (float)) else ""}}'
            + f'<br>{nAlloc_begin_luminosity_block_pr:{".2f" if isinstance(nAlloc_begin_luminosity_block_pr, (float)) else ""}}'
            + f'<br>{nAlloc_begin_luminosity_block_diff:{".2f" if isinstance(nAlloc_begin_luminosity_block_diff, (float)) else ""}}</td>'
        ]
        nAlloc_event_ib = (
            moduleres.get("nAlloc event IB", "N/A")
            if isinstance(moduleres.get("nAlloc event IB", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_event_pr = (
            moduleres.get("nAlloc event PR", "N/A")
            if isinstance(moduleres.get("nAlloc event PR", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_event_diff = (
            moduleres.get("nAlloc event diff", "N/A")
            if isinstance(moduleres.get("nAlloc event diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{nAlloc_event_ib:{".2f" if isinstance(nAlloc_event_ib, (float)) else ""}}'
            + f'<br>{nAlloc_event_pr:{".2f" if isinstance(nAlloc_event_pr, (float)) else ""}}'
            + f'<br>{nAlloc_event_diff:{".2f" if isinstance(nAlloc_event_diff, (float)) else ""}}</td>'
        ]
        nAlloc_event_setup_ib = (
            moduleres.get("nAlloc event setup IB", "N/A")
            if isinstance(moduleres.get("nAlloc event setup IB", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_event_setup_pr = (
            moduleres.get("nAlloc event setup PR", "N/A")
            if isinstance(moduleres.get("nAlloc event setup PR", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_event_setup_diff = (
            moduleres.get("nAlloc event setup diff", "N/A")
            if isinstance(moduleres.get("nAlloc event setup diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{nAlloc_event_setup_ib:{".2f" if isinstance(nAlloc_event_setup_ib, (float)) else ""}}'
            + f'<br>{nAlloc_event_setup_pr:{".2f" if isinstance(nAlloc_event_setup_pr, (float)) else ""}}'
            + f'<br>{nAlloc_event_setup_diff:{".2f" if isinstance(nAlloc_event_setup_diff, (float)) else ""}}</td>'
        ]
        nAlloc_total_ib = (
            (
                moduleres.get("nAlloc event setup IB", "N/A")
                + moduleres.get("nAlloc event IB", "N/A")
                + moduleres.get("nAlloc construction IB", "N/A")
            )
            if isinstance(moduleres.get("nAlloc event setup IB", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc construction IB", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc event IB", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_total_pr = (
            (
                moduleres.get("nAlloc event setup PR", "N/A")
                + moduleres.get("nAlloc event PR", "N/A")
                + moduleres.get("nAlloc construction PR", "N/A")
            )
            if isinstance(moduleres.get("nAlloc event setup PR", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc construction PR", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc event PR", "N/A"), (int, float))
            else "N/A"
        )
        nAlloc_total_diff = (
            (
                moduleres.get("nAlloc event setup diff", "N/A")
                + moduleres.get("nAlloc event diff", "N/A")
                + moduleres.get("nAlloc construction diff", "N/A")
            )
            if isinstance(moduleres.get("nAlloc event setup diff", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc construction diff", "N/A"), (int, float))
            and isinstance(moduleres.get("nAlloc event diff", "N/A"), (int, float))
            else "N/A"
        )
        summaryLines += [
            '<td align="right">'
            + f'{nAlloc_total_ib:{".2f" if isinstance(nAlloc_total_ib, (float)) else ""}}'
            + f'<br>{nAlloc_total_pr:{".2f" if isinstance(nAlloc_total_pr, (float)) else ""}}'
            + f'<br>{nAlloc_total_diff:{".2f" if isinstance(nAlloc_total_diff, (float)) else ""}}</td>'
        ]
        transitions_ib = (
            moduleib.get("transitions", "N/A")
            if isinstance(moduleib.get("transitions", "N/A"), (int, float))
            else "N/A"
        )
        transitions_pr = (
            modulepr.get("transitions", "N/A")
            if isinstance(modulepr.get("transitions", "N/A"), (int, float))
            else "N/A"
        )
        if isinstance(transitions_ib, (int, float)) and isinstance(transitions_pr, (int, float)):
            transitions_diff = transitions_ib - transitions_pr
        else:
            if not isinstance(transitions_ib, (int, float)) and isinstance(
                transitions_pr, (int, float)
            ):
                transitions_diff = transitions_pr - 0
            elif isinstance(transitions_ib, (int, float)) and not isinstance(
                transitions_pr, (int, float)
            ):
                transitions_diff = 0 - transitions_ib
        summaryLines += [
            '<td align="right">'
            + f'{transitions_ib:{".2f" if isinstance(transitions_ib, (float)) else ""}}'
            + f'<br>{transitions_pr:{".2f" if isinstance(transitions_pr, (float)) else ""}}'
            + f'<br>{transitions_diff:{".2f" if isinstance(transitions_diff, (float)) else ""}}</td>'
        ]

summaryLines += []
summaryLines += ["</body></html>"]

summaryFile = (
    os.path.dirname(os.path.realpath(sys.argv[2]))
    + "/diff-"
    + os.path.basename(os.path.realpath(sys.argv[2]))
    + ".html"
)
with open(summaryFile, "w") as g:
    for summaryLine in summaryLines:
        print(summaryLine, file=g)
