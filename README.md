# OSHW Export for Alibre

## What problem does this solve?

I use Alibre for open-source hardware designs, because for me personally, FreeCAD is not quite "there" yet. I can work much more quickly, and document my designs more clearly, using Alibre. However, even with Alibre's new PDM functionality, I still want to store and version my Alibre designs in an open-source-friendly manner.

For most electromechanical devices, the GitHub "monorepo" approach is my default - I like to store _everything_ (software, MCAD files, ECAD files, and documentation) in a single repository, so each Release from that repository is a complete snapshot of the product.

The best way to store an Alibre mechanical design in a Git repository is to use the Package feature. However, this has one notable flaw: potential contributors _without_ Alibre licenses cannot even view the models, much less modify them. The hardware is only _really_ open-source once you've paid for an Alibre license. This is, of course, not ideal.

The best solution to this problem is to export neutral files, in addition to the "Native" Alibre Design files. There are two good candidates for this:
* **STEP Files:** This is a "universal" neutral file. Practically every CAD software will accept this file type, but it does require translation, so it is occasionally subject to data loss/errors.
* **SAT Files:** This is the "native tongue" of the ACIS modeling kernel, which is the kernel Alibre uses under the hood. In theory, these files should be the _least_ error-prone, while still remaining "neutral" (unlike proprietary Alibre files).

In most cases, files should be exported at 3 levels:
* **Top-Level Assembly:** This would be the complete device (e.g. ``MyEntireWidget.stp``).
* **Subassemblies:** Any subassemblies should be exported individually, in case subassembly-level models are needed for procurement or manufacturing.
* **Parts:** Parts should be exported individually, to support manufacturing and procurement. For instance, although ``MyEntireWidget.stp`` contains all the necessary subcomponents, it is a hassle to "separate" the components in a STEP file. By exporting neutral files for each part, ``MyPlasticPart.stp`` can be 3D-printed exactly as-is, with no need to open up modeling software and "isolate" it manually.

## Folder Structure

Right now, the folder structure is extremely simple:
* ``AlibreScript.py`` : This is a "dummy" file containing _most_ (not all!) of the Alibre Script API, solely for the purpose of linting and code completion. [I didn't make this, it's available under the MIT license, courtesy of @stephensmitchell.](https://github.com/stephensmitchell/alibre-script/tree/master/Alibre-Script-Stub-Files)
* ``export_all_neutral_files_recursive.py`` : This is the actual export script. Run this from inside the Alibre Script window.
* ``README.md`` : _You are here._

## Future Feature Goals

I'd ultimately like to provide the option for a configuration file to be stored in the repo, governing the export tool. It would probably need to be JSON, since the ``json`` module is one of the few available in the IronPython interpreter that Alibre ships with. This file would facilitate project-specific behaviors, such as:
* **Defining the Alibre Version used in the native files.** This could be important if collaborators are running slightly older versions of Alibre.
* **Including and excluding certain components from the export process.** For example, if a particular subassembly is only purchaseable as a complete unit (not as separate subcomponents), then there is likely no reason to export its subcomponents to their own neutral files.
* **Defining naming conventions and folder-structure conventions for the exported files.** For example, some projects might wish for the exported files' names to include the Part Number property, in addition to the name in Alibre (e.g. ``109ABCD_MySheetMetalThing.sat``).
* **Defining, on a per-component basis, which types of files should be exported** (STEP AP203, STEP AP214, STL, SAT, etc)
* **Defining if/how metadata (Alibre Properties) should be exported for each file.** For example, Part Number, Estimated Cost, Vendor Weblinks, etc. Some of these may be desirable to export, while in an OSHW-based business context, some of these may _not_ be desirable to export (you may wish to keep your vendor relationships private even as your designs are open).
* **Defining required "manual exports", such as BOMs/PDFs/DXFs, on a per-component basis.** Alibre Script cannot currently do anything with BOM files or drawing files, so a fully-automated "Export BOM to CSV" and "Export Drawing to PDF/DXF" is off the table. In fact, Alibre Script has no way to find out if a part/assembly even has an accompanying BOM or drawing - the only system that would have this information is the new Alibre PDM, which has no public-facing API at this point. With these limitations in mind, I think the best compromise would be to include "flags" in the configuration file that indicate which components "require" a BOM or a drawing (and perhaps which file types should be exported for those items). Then this export tool could remind the user to manually export these items, and a good CI/CD pipeline could ensure that when MCAD files are modified, these items get modified as well.

Finally, I'd like the script to (optionally) output a log file, so that the CI/CD pipeline in a Git repo could check if any errors occurred (that we know of) during the export process. Some parts (particularly those imported from another CAD package in the first place) may fail to export to STEP, and this should be visible to CI/CD processes, so these issues can be addressed before a Pull Request is merged or a Release is shipped.
