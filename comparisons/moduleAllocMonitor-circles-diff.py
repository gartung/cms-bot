#! /usr/bin/env python3

import sys
import json
import os
import math


def diff_from(metrics, data, dest, res):
    for metric in metrics:
        ibkey = "%s IB" % metric
        res[ibkey] = data.get(metric, float("nan"))
        prkey = "%s PR" % metric
        res[prkey] = dest.get(metric, float("nan"))
        if math.isnan(res[ibkey]) or math.isnan(res[prkey]):
            res[metric + " diff"] = float("nan")
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
threshold = 5000.0
error_threshold = 20000.0


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
            modulepr.get("added event setup", float("nan"))
            + modulepr.get("added event", float("nan"))
            + modulepr.get("added construction", float("nan"))
            + modulepr.get("added global begin run", float("nan"))
            + modulepr.get("added stream begin run", float("nan"))
            + modulepr.get("added global begin luminosity block", float("nan"))
            + modulepr.get("added stream begin luminosity block", float("nan"))
        )
        added_total_ib = (
            moduleib.get("added event setup", float("nan"))
            + moduleib.get("added event", float("nan"))
            + moduleib.get("added construction", float("nan"))
            + moduleib.get("added global begin run", float("nan"))
            + moduleib.get("added stream begin run", float("nan"))
            + moduleib.get("added global begin luminosity block", float("nan"))
            + moduleib.get("added stream begin luminosity block", float("nan"))
        )
        added_total_diff = (
            moduleres.get("added event setup diff", float("nan"))
            + moduleres.get("added event diff", float("nan"))
            + moduleres.get("added construction diff", float("nan"))
            + moduleres.get("added global begin run diff", float("nan"))
            + moduleres.get("added stream begin run diff", float("nan"))
            + moduleres.get("added global begin luminosity block diff", float("nan"))
            + moduleres.get("added stream begin luminosity block diff", float("nan"))
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
    key=lambda x: x[1].get("added total diff", float("nan")),
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
        if moduleres.get("added total diff", float("nan")) == math.nan:
            print("Error: module %s is not in diff results" % key)
            continue
        cellString = '<td align="right" '
        color = ""
        addedtotaldiff = moduleres.get("added total diff", float("nan"))
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
            '<td align="right"> %0.2f<br> %0.2f<br> %0.2f</td>'
            % (
                moduleib.get("added construction", float("nan")),
                modulepr.get("added construction", float("nan")),
                moduleres.get("added construction diff", float("nan")),
            ),
            '<td align="right"> %0.2f<br> %0.2f<br> %0.2f</td>'
            % (
                moduleib.get("added global begin run", float("nan"))
                + moduleib.get("added stream begin run", float("nan")),
                modulepr.get("added global begin run", float("nan"))
                + modulepr.get("added stream begin run", float("nan")),
                moduleres.get("added global begin run diff", float("nan"))
                + moduleres.get("added stream begin run diff", float("nan")),
            ),
            '<td align="right"> %0.2f<br> %0.2f<br> %0.2f</td>'
            % (
                moduleib.get("added global begin luminosity block", float("nan"))
                + moduleib.get("added stream begin luminosity block", float("nan")),
                modulepr.get("added global begin luminosity block", float("nan"))
                + modulepr.get("added stream begin luminosity block", float("nan")),
                moduleres.get("added global begin luminosity block diff", float("nan"))
                + moduleres.get("added stream begin luminosity block diff", float("nan")),
            ),
            '<td align="right"> %0.2f<br> %0.2f<br> %0.2f</td>'
            % (
                moduleib.get("added event", float("nan")),
                modulepr.get("added event", float("nan")),
                moduleres.get("added event diff", float("nan")),
            ),
            '<td align="right"> %0.2f<br> %0.2f<br> %0.2f</td>'
            % (
                moduleib.get("added event setup", float("nan")),
                modulepr.get("added event setup", float("nan")),
                moduleres.get("added event setup diff", float("nan")),
            ),
            cellString
            + "%0.2f<br> %0.2f<br> %0.2f</td>"
            % (
                moduleib.get("added event setup", float("nan"))
                + moduleib.get("added event", float("nan"))
                + moduleib.get("added construction", float("nan"))
                + moduleib.get("added global begin run", float("nan"))
                + moduleib.get("added stream begin run", float("nan"))
                + moduleib.get("added global begin luminosity block", float("nan"))
                + moduleib.get("added stream begin luminosity block", float("nan")),
                modulepr.get("added event setup", float("nan"))
                + modulepr.get("added event", float("nan"))
                + modulepr.get("added construction", float("nan"))
                + modulepr.get("added global begin run", float("nan"))
                + modulepr.get("added stream begin run", float("nan"))
                + modulepr.get("added global begin luminosity block", float("nan"))
                + modulepr.get("added stream begin luminosity block", float("nan")),
                moduleres.get("added event setup diff", float("nan"))
                + moduleres.get("added event diff", float("nan"))
                + moduleres.get("added construction diff", float("nan"))
                + moduleres.get("added global begin run diff", float("nan"))
                + moduleres.get("added stream begin run diff", float("nan"))
                + moduleres.get("added global begin luminosity block diff", float("nan"))
                + moduleres.get("added stream begin luminosity block diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc construction", float("nan")),
                modulepr.get("nAlloc construction", float("nan")),
                moduleres.get("nAlloc construction diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc global begin run", float("nan"))
                + moduleib.get("nAlloc stream begin run", float("nan")),
                modulepr.get("nAlloc global begin run", float("nan"))
                + modulepr.get("nAlloc stream begin run", float("nan")),
                moduleres.get("nAlloc global begin run diff", float("nan"))
                + moduleres.get("nAlloc stream begin run diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc global begin luminosity block", float("nan"))
                + moduleib.get("nAlloc stream begin luminosity block", float("nan")),
                modulepr.get("nAlloc global begin luminosity block", float("nan"))
                + modulepr.get("nAlloc stream begin luminosity block", float("nan")),
                moduleres.get("nAlloc global begin luminosity block diff", float("nan"))
                + moduleres.get("nAlloc stream begin luminosity block diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc event", float("nan")),
                modulepr.get("nAlloc event", float("nan")),
                moduleres.get("nAlloc event diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc event setup", float("nan")),
                modulepr.get("nAlloc event setup", float("nan")),
                moduleres.get("nAlloc event setup diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("nAlloc event setup", float("nan"))
                + moduleib.get("nAlloc event", float("nan"))
                + moduleib.get("nAlloc construction", float("nan")),
                modulepr.get("nAlloc event setup", float("nan"))
                + modulepr.get("nAlloc event", float("nan"))
                + modulepr.get("nAlloc construction", float("nan")),
                moduleres.get("nAlloc event setup diff", float("nan"))
                + moduleres.get("nAlloc event diff", float("nan"))
                + moduleres.get("nAlloc construction diff", float("nan")),
            ),
            '<td align="right">%0.f<br>%0.f<br>%0.f</td>'
            % (
                moduleib.get("transitions", float("nan")),
                modulepr.get("transitions", float("nan")),
                moduleres.get("transitions diff", float("nan")),
            ),
            "</tr>",
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
