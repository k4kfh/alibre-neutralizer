# -- ALIBRE NEUTRALIZER --
# Parametric Bulk-Exporter for Alibre Design
# -------------------------------------------
# https://github.com/k4kfh/alibre-neutralizer
# Released under the LGPL 3.0 License

# import for auto-completion/code hints in development
from AlibreScript import *

# real dependencies
import os
import re
import xml.etree.ElementTree as ET
import csv

class ExportTypes:
    """AlibreScript's IronPython interpreter doesn't have the Enum library available, so this was my best shot at fudging enum-ish behavior."""
    STEP203 = 1
    STEP214 = 2
    SAT = 3
    STL = 4
    IGES = 5
    CSV_Properties = 6
    CSV_Parameters = 7

    # Static utility method
    @staticmethod
    def get_file_extensions(export_type):
        """Given an integer representing an export file type, return a list of possible file extensions corresponding to that export file type."""
        if (export_type == ExportTypes.STEP203) or (export_type == ExportTypes.STEP214):
            return [".stp", ".step"]
        elif (export_type == ExportTypes.SAT):
            return [".sat"]
        elif (export_type == ExportTypes.STL):
            return [".stl"]
        elif (export_type == ExportTypes.IGES):
            return [".iges", ".igs"]
        elif (export_type == ExportTypes.CSV_Properties) or (export_type == ExportTypes.CSV_Parameters):
            return [".csv"]
        else:
            raise Exception("Invalid export type provided.")
    
    @staticmethod
    def convert_to_string(export_type):
        """Given an integer export type, return a string (like 'STEP203')."""
        if export_type == ExportTypes.STEP203:
            return "STEP203"
        elif export_type == ExportTypes.STEP214:
            return "STEP214"
        elif export_type == ExportTypes.SAT:
            return "SAT"
        elif export_type == ExportTypes.STL:
            return "STL"
        elif export_type == ExportTypes.IGES:
            return "IGES"
        elif export_type == ExportTypes.CSV_Properties:
            return "CSV of Component Properties"
        elif export_type == ExportTypes.CSV_Parameters:
            return "CSV of Component Parameters"

class ExportDirective:
    """Each instance of this directs AssemblyNeutralizer to export a particular type of file, with a particular relative path and filename.
    For example, a STEP214 export to ./whatever/relative/path/{FileName}_{Revision}.stp ."""

    def __init__(self, export_type, export_rel_path_expression, purge_directory_before_export=None, export_root_assembly=True, export_subassemblies=True, export_parts=True):
        # type: (ExportDirective, int, str, None | str, bool, bool, bool) -> None
        """
        Define a new Export Directive. You'll need one of these for each type of file you want to export.

        :param export_type: Specify a single file type for this export. See the ExportTypes "static" class for options.
        :type export_type: str

        :param export_rel_path_expression: Specify a formula for the relative path of each exported file, using Python string .format syntax.
        For example, ``./whatever/relative/path/{FileName}_{Revision}.stp``. Available variables are: TODO
        :type export_rel_path_expression: str

        :param purge_directory_before_export: Set to a path (relative to the root assembly) that you'd like purged of your selected export type (.stp, .sat, etc) before exporting.
        If set to None (the default), no files will be deleted before exporting new ones (although new files may overwrite old files).

        :param export_root_assembly: Set to False to skip exporting the root assembly with this Export Directive.
        :type export_root_assembly: bool

        :param export_subassemblies: Set to False to skip exporting subassemblies with this Export Directive.
        :type export_subassemblies: bool

        :param export_parts: Set to False to skip exporting individual parts with this Export Directive.
        :type export_parts: bool
        """
        # Core Export Settings
        
        # TODO: Data validation
        self.export_type = export_type

        # TODO: Data validation
        self.export_rel_path_expression = export_rel_path_expression

        # TODO: Data validation on the relative path syntax, if it's not set to None
        self.purge_before_export = purge_directory_before_export

        # Store data on which types of components we should export
        self.export_root_assembly = export_root_assembly
        self.export_subassemblies = export_subassemblies
        self.export_parts = export_parts
    
    def get_export_path(self, component):
        """Given a Part or Subassembly or Assembly, return the relative Export path based on the expression in ``export_rel_path_expression``.
        
        :type self: ExportDirective

        :param component: The component (Part or Assembly) whose export path you want to evaluate.
        :type component: Assembly | Part | Subassembly | AssembledPart
        """
        # A smidge of type enforcement
        if not (
            isinstance(component, Part)
            or isinstance(component, AssembledPart)
            or isinstance(component, AssembledSubAssembly)
            or isinstance(component, Assembly)
        ):
            raise Exception("Expected a Part or Assembly, but did not receive one.")
        
        # At this point we can safely assume we have an Alibre Part/Assembly
        component_properties_prettified = self.get_prettified_component_properties(component)
        
        path_unsanitized = os.path.normpath(
            self.export_rel_path_expression.format(
                Comment = component_properties_prettified["Comment"],
                CostCenter = component_properties_prettified["CostCenter"],
                CreatedBy = component_properties_prettified["CreatedBy"],
                CreatedDate = component_properties_prettified["CreatedDate"],
                CreatingApplication = component_properties_prettified["CreatingApplication"],
                Density = component_properties_prettified["Density"],
                Description = component_properties_prettified["Description"],
                DocumentNumber = component_properties_prettified["DocumentNumber"],
                EngineeringApprovalDate = component_properties_prettified["EngineeringApprovalDate"], 
                EngineeringApprovedBy = component_properties_prettified["EngineeringApprovedBy"],
                EstimatedCost = component_properties_prettified["EstimatedCost"],
                FileName = component_properties_prettified["FileName"],
                Keywords = component_properties_prettified["Keywords"],
                LastAuthor = component_properties_prettified["LastAuthor"],
                LastUpdateDate = component_properties_prettified["LastUpdateDate"],
                ManufacturingApprovedBy = component_properties_prettified["ManufacturingApprovedBy"],
                ModifiedInformation = component_properties_prettified["ModifiedInformation"],
                Name = component_properties_prettified["Name"],
                Number = component_properties_prettified["Number"],
                Product = component_properties_prettified["Product"],
                ReceivedFrom = component_properties_prettified["ReceivedFrom"],
                Revision = component_properties_prettified["Revision"],
                StockSize = component_properties_prettified["StockSize"],
                Supplier = component_properties_prettified["Supplier"],
                Title = component_properties_prettified["Title"],
                Vendor = component_properties_prettified["Vendor"],
                WebLink = component_properties_prettified["WebLink"],
            )
        )

        # Scrub out some illegal characters from the relative portion of the path
        # These sometimes sneak in as part of the names of the Alibre files
        # Since we have put the path through os.path.normpath() already, we can avoid escaping out any important separators
        # by simply escaping os.sep character.
        pattern = r'[^\w_.: \-' + re.escape(os.sep) + r']'
        path_sanitized = re.sub(pattern, '_', path_unsanitized)

        return path_sanitized

    def get_prettified_component_properties(self, component):
        """Return a dictionary of Alibre component properties (such as Number, CostCenter, etc).
        The only difference over the 'raw' data is that this dictionary will replace any totally-empty values
        with 'Undefined {whatever}', where {whatever} is the name of the property (e.g. 'Cost Center').
        
        This ensures that if you use these values as folders or portions of filenames, you don't end up with random empty spaces or other strange quirks."""
        # type: (ExportDirective, Part | Assembly | AssembledPart | AssembledSubAssembly)

        # Create skeleton
        component_prettified_properties = {
            "Comment" : None,
            "CostCenter" : None,
            "CreatedBy" : None,
            "CreatedDate" : None,
            "CreatingApplication" : None,
            "Density" : None,
            "Description" : None,
            "DocumentNumber" : None,
            "EngineeringApprovalDate" : None,
            "EngineeringApprovedBy" : None,
            "EstimatedCost" : None,
            "FileName" : None,
            "Keywords" : None,
            "LastAuthor" : None,
            "LastUpdateDate" : None,
            "ManufacturingApprovedBy" : None,
            "ModifiedInformation" : None,
            "Name" : None,
            "Number" : None,
            "Product" : None,
            "ReceivedFrom" : None,
            "Revision" : None,
            "StockSize" : None,
            "Supplier" : None,
            "Title" : None,
            "Vendor" : None,
            "WebLink" : None,
        }

        default_values = [
            ("Comment", "Undefined Comment"),
            ("CostCenter", "Undefined Cost Center"),
            ("CreatedBy", "Undefined Creator"),
            ("CreatedDate", "Undefined Creation Date"),
            ("CreatingApplication", "Undefined Creating Application"),
            ("Density", "Undefined Density"),
            ("Description", "Undefined Description"),
            ("DocumentNumber", "Undefined Document Number"),
            ("EngineeringApprovalDate", "Undefined Engineering Approval Date"),
            ("EngineeringApprovedBy", "Undefined Engineering Approver"),
            ("EstimatedCost", "Undefined Estimated Cost"),
            ("FileName", "Undefined File Name"),
            ("Keywords", "Undefined Keywords"),
            ("LastAuthor", "Undefined Last Author"),
            ("LastUpdateDate", "Undefined Last Update Date"),
            ("ManufacturingApprovedBy", "Undefined Manufacturing Approved By"),
            ("ModifiedInformation", "Undefined Modified Information"),
            ("Name", "Undefined Name"),
            ("Number", "Undefined Part Number"),
            ("Product", "Undefined Product"),
            ("ReceivedFrom", "Undefined Received From"),
            ("Revision", "Undefined Revision"),
            ("StockSize", "Undefined Stock Size"),
            ("Supplier", "Undefined Supplier"),
            ("Title", "Undefined Title"),
            ("Vendor", "Undefined Vendor"),
            ("WebLink", "Undefined Web Link"),
        ]

        for key, default_string in default_values:
            # Use the getattr() function to safely access the component's attribute
            component_value = getattr(component, key, None)

            # The expression `not component_value` handles None, 0, and empty string ("")
            # For properties that should specifically only default on None or "",
            # you can use `if component_value is None or component_value == "":`
            if component_value is None or component_value == "":
                component_prettified_properties[key] = default_string
            else:
                # Otherwise, assign the actual value from the component object
                component_prettified_properties[key] = component_value
        
        return component_prettified_properties

    def get_extensions_to_purge(self):
        """Return the list of extensions which should be purged before a new export.
        If the purge functionality is disabled, return an empty list."""
        # type: (ExportDirective) -> list[str]
        if self.purge_before_export == None:
            return [] # Returning an empty list means "purge no files"
        else:
            return ExportTypes.get_file_extensions(self.export_type)

class AlibreNeutralizer:
    """Create an instance of this, with an Alibre Assembly passed in, to handle the backend logic of recursively exporting files."""

    def __init__(self, component, config_file_path):
        # type: (AlibreNeutralizer, Assembly | AssembledSubAssembly, str) -> None
        """Create and configure an instance of AlibreNeutralizer from an XML configuration file.
        
        :type self: AlibreNeutralizer

        :param component: The top-level assembly that you want to recursively export.
        :type component: Assembly | AssembledSubAssembly

        :param config_file_path: Path to the XML configuration file that defines the export configuration.
        :type config_file_path: str
        """

        # Store the root assembly or part, our main connection point to Alibre
        if isinstance(component, Assembly):
            self.root_component = component
        else:
            raise Exception("Cannot initialize AssemblyNeutralizer without a valid Alibre Assembly object.")

        # Read the configuration file
        tree = ET.parse(config_file_path)
        root = tree.getroot()
        
        # Store the config file path.
        # This is used to interpret the "Base Path" from the config file, since it's specified RELATIVE to the config file's location.
        self.config_file_path = config_file_path
        # Get the base path from config
        base_path_elem = root.find('BaseExportPath')
        self.base_path = os.path.normpath(base_path_elem.text) if base_path_elem is not None and base_path_elem.text is not None else os.path.normpath('.')
        
        # Parse export directives from config
        self.export_directives = []
        for directive in root.find('ExportDirectiveList').findall('ExportDirective'):
            export_type = getattr(ExportTypes, directive.find('type').text)
            path_expression = directive.find('RelativeExportPath').text
            purge_directory = directive.find('PurgeDirectoryBeforeExporting').text if directive.find('PurgeDirectoryBeforeExporting') is not None else None

            # Read boolean flags (default to True if the element is missing)
            def _bool_from_elem(elem, default=True):
                if elem is None or elem.text is None:
                    return default
                val = elem.text.strip().lower()
                return val in ("true", "1", "yes", "y")

            enable_root = _bool_from_elem(directive.find('EnableRootAssemblyExport'), True)
            enable_sub = _bool_from_elem(directive.find('EnableSubassemblyExport'), True)
            enable_part = _bool_from_elem(directive.find('EnablePartExport'), True)

            self.export_directives.append(
                ExportDirective(
                    export_type=export_type,
                    export_rel_path_expression=path_expression,
                    purge_directory_before_export=purge_directory,
                    export_root_assembly=enable_root,
                    export_subassemblies=enable_sub,
                    export_parts=enable_part
                )
            )

    
    def export_all(self):
        """Carry out the ExportDirectives in ``self.export_directives`` on the Part or Assembly in ``self.root_component.``"""

        processed_files = set() # This will be a set of file absolute paths that we've processed (run export directives against).
        # This ensures we only export each component once.
        # Even if the export directive says not to export anything for a given file, we still add that file to the "processed" list.
        # Note that we use absolute paths (e.g. C:\wherever\myThing.AD_PRT) over Alibre's .Name property, because .Name includes the instance ID (the "<37>" type thing) at the end, while the filename does not.
        # May need to change this in the future if we want to export directly from PDM instead of from a package, since FileName is None in PDM.

        # Step 1: Purge old files, if applicable
        for edir in self.export_directives:
            self._purge_according_to_export_directive(edir)
        
        # Step 2 : Export the Root Assembly
        # if none of the export directives call for this, this function won't do anything
        self._export_root_assembly()

        # Step 3: Export parts in root assembly, and add those parts to the exported_files list
        processed_files = processed_files.union(
            self._export_parts(self.root_component, self.export_directives, processed_files)
        )

        # Step 4: Export subassemblies in root assembly (recursive)
        # for subassy in subassemblies
        #   for edir in export_directives
        #     newly_exported_names = _export_subassembly_recursive(component, edir)
        #     exported_files.append(newly_exported_names)
        for subassy in self.root_component.SubAssemblies:
            processed_files = processed_files.union(
                self._export_subassemblies_recursive(subassy, self.export_directives, processed_files)
            )

    def _export_parts(self, assembly, export_directives, already_processed_files):
        """Given an Assembly (or AssembledSubAssembly), an ExportDirective, and a list of already-exported files to ignore,
        export the parts in the assembly according to the ExportDirective, and return an updated list of exported files."""
        # type (AlibreNeutralizer, Assembly | AssembledSubAssembly, list[ExportDirective], set[str]) -> set[str]

        for part in assembly.Parts:
            # First, make sure we haven't processed this one already
            if part.FileName not in already_processed_files:
                # Run through all the export directives on this part
                for edir in export_directives:
                    self._execute_single_export_directive(part, edir)
                # Once all Export Directives have been executed, add it to the list of exports
                already_processed_files = already_processed_files.union({part.FileName})

        return already_processed_files

    def _export_root_assembly(self):
        """If any of the Export Directives call for it, export the Root Assembly (``self.root_component``)."""
        # type (AlibreNeutralizer)

        for export_directive in self.export_directives:
            if (export_directive.export_root_assembly == True):
                # We need to export this root Assembly
                print "- Exporting Root Assembly to {0}: {1}".format(ExportTypes.convert_to_string(export_directive.export_type), self.root_component.Name)
                abs_export_path = self._get_absolute_export_path(
                    export_directive.get_export_path(self.root_component)
                )
                print "- Path : {0}".format(abs_export_path)
                self._export(
                    self.root_component,
                    export_directive.export_type,
                    abs_export_path
                )

    def _export_subassemblies_recursive(self, subassembly, export_directives, already_processed_files):
        # type (AlibreNeutralizer, AssembledSubAssembly, list[ExportDirective], set[str]) -> set[str]

        # Step 1 : Export parts
        # If the export directives have "Export Parts" set to False, this code won't do anything
        # Also, if any of these parts have already been exported, they'll be skipped automatically in this function
        already_processed_files = already_processed_files.union(
            self._export_parts(subassembly, export_directives, already_processed_files)
        )

        # Step 2 : Export this subassembly
        for edir in export_directives:
            self._execute_single_export_directive(subassembly, edir)
        already_processed_files = already_processed_files.union({subassembly.FileName})

        # Step 3: Recurse
        for subsubassy in subassembly.SubAssemblies:
            if subsubassy.FileName not in already_processed_files:
                already_processed_files = already_processed_files.union(
                    self._export_subassemblies_recursive(subsubassy, export_directives, already_processed_files)
                )

        return already_processed_files

    def _purge_according_to_export_directive(self, export_directive):
        """Given an ExportDirective, delete any old files it's configured to purge. This should be called before exporting any new files."""
        # type: (AlibreNeutralizer, ExportDirective) -> None
        
        # Recursively purge files with extensions listed in export_directive.
        for file_extension in export_directive.get_extensions_to_purge():
            # Recursive purge files of type ".{fileExtension}" from self._convert_base_path_to_absolute() + export_directive.purge_before_export

            # Purge path = export_directive.purge_before_export, relative to self._convert_base_path_to_absolute()
            purge_path = os.path.normpath(
                os.path.join(
                    self._convert_base_path_to_absolute(),
                    os.path.normpath(export_directive.purge_before_export)
                )
            )

            # Recursively purge files of type fileExtension in purge_path and subdirectories
            for root, _, files in os.walk(purge_path):
                for file in files:
                    if file.endswith(file_extension):
                        file_path = os.path.join(root, file)
                        try:
                            # TODO: uncomment to do it for realsies
                            os.remove(file_path)
                        except OSError as e:
                            print "ERROR: Could not delete {file_path} in pre-export purge: {e}".format(file_path=file_path, e=e)

    def _execute_single_export_directive(self, component, export_directive):
        """Given a ``Part`` or ``Assembly``, execute one ``ExportDirective`` against it. This function does NOT perform any deduplication checking."""
        # type: (AlibreNeutralizer, Part, ExportDirective | list[ExportDirective]) -> None
        
        if not (
            isinstance(component, AssembledPart)
            or isinstance(component, Part)
            or isinstance(component, AssembledSubAssembly)
            or isinstance(component, Assembly)):
            raise Exception("Invalid argument. Expected a Part, AssembledPart, AssembledSubAssembly, or Assembly.")

        if isinstance(export_directive, ExportDirective):
            # Confirmed: We have a valid ExportDirective.
            # Now we need to read that ExportDirective and compare it against the type of component we're dealing with.
            # This will dictate whether we actually need to export this component.
            if export_directive.export_parts == True and (isinstance(component, AssembledPart) or isinstance(component, Part)):
                # We need to export this Part
                print "- Exporting Part to {0}: {1}".format(ExportTypes.convert_to_string(export_directive.export_type), component.Name)
                abs_export_path = self._get_absolute_export_path(
                    export_directive.get_export_path(component)
                )
                print "- Path : {0}".format(abs_export_path)
                self._export(
                    component,
                    export_directive.export_type,
                    abs_export_path
                )
            elif (export_directive.export_subassemblies == True) and isinstance(component, AssembledSubAssembly):
                # We need to export this Subassembly
                print "- Exporting Subassembly to {0}: {1}".format(ExportTypes.convert_to_string(export_directive.export_type), component.Name)
                abs_export_path = self._get_absolute_export_path(
                    export_directive.get_export_path(component)
                )
                print "- Path : {0}".format(abs_export_path)
                self._export(
                    component,
                    export_directive.export_type,
                    abs_export_path
                )


        else:
            raise Exception("Invalid argument - expected an ExportDirective.")
    
    def _export(self, component, export_type, export_path_abs):
        """Given a Part or Assembly, export the specified file type to the specified absolute path."""
        # type: (AlibreNeutralizer, Part | Assembly, int, str) -> None

        # Make sure the full directory tree exists. If it doesn't create it
        export_directory = os.path.dirname(export_path_abs)
        if not os.path.exists(export_directory):
            os.makedirs(export_directory)
        
        # TODO: Better error handling/logging than this.
        # This gets the job done for testing the path interpretations.
        try:
            if export_type == ExportTypes.SAT:
                component.ExportSAT(export_path_abs, 0, True) # TODO: Figure out an appropriate File Version (probably not 0)
            elif export_type == ExportTypes.STEP203:
                component.ExportSTEP203(export_path_abs)
            elif export_type == ExportTypes.STEP214:
                component.ExportSTEP214(export_path_abs)
            elif export_type == ExportTypes.IGES:
                component.ExportIGES(export_path_abs)
            elif export_type == ExportTypes.STL:
                component.ExportSTL(export_path_abs)
            elif export_type == ExportTypes.CSV_Properties:
                # Export Properties (metadata like Cost Center, Part Number, etc) to CSV
                self._export_properties_to_csv(component, export_path_abs)
            elif export_type == ExportTypes.CSV_Parameters:
                # Export Parameters (dimensions, equations, etc) to CSV
                self._export_parameters_to_csv(component, export_path_abs)
        except Exception as e:
            print "ERROR: There was a problem exporting {0} to {1} format.".format(component.FileName, ExportTypes.convert_to_string(export_type))
    
    def _convert_base_path_to_absolute(self):
        """Convert self.base_path to an absolute path, relative to the directory where the config file lives.
        In the rare case that self.base_path is already absolute, just return it as-is.
        
        This serves as the 'base' path for individual file export paths."""
        # type: (AlibreNeutralizer) -> str

        if os.path.isabs(self.base_path):
            return self.base_path
        else:
            # It's not absolute. We need to make it absolute.
            root_assembly_dir = os.path.dirname(
                os.path.normpath(self.config_file_path)
            )
            return os.path.normpath(os.path.join(root_assembly_dir, self.base_path))
    
    def _get_absolute_export_path(self, export_path_relative):
        """Combine a given relative export path with this ``AlibreNeutralizer``'s absolute ``base_path``, to give an absolute path."""


        # Scrub out some illegal characters from the relative portion of the path
        # These sometimes sneak in as part of the names of the Alibre files
        pattern = r'[^\w_.: \-' + re.escape(os.sep) + r']'
        export_path_relative_sanitized = re.sub(pattern, '_', export_path_relative)

        return os.path.normpath(
            os.path.join(
                self._convert_base_path_to_absolute(),
                export_path_relative_sanitized
            )
        )

    def _export_properties_to_csv(self, component, export_path_abs):
        """Given a single Part or Assembly, export its Properties (Comment, Cost Center, Part Number, etc) to a CSV file at a specified path."""
        # type: (AlibreNeutralizer, Part | Assembly, str) -> None

        # If you don't put "wb" here, it puts an extra blank row between every row
        with open(export_path_abs, 'wb') as csv_file:
            writer = csv.writer(csv_file)

            # File header
            writer.writerow(["Property Name", "Value"])

            # File contents
            data = [
                ["Comment", component.Comment],
                ["CostCenter", component.CostCenter],
                ["CreatedBy", component.CreatedBy],
                ["CreatedDate", component.CreatedDate],
                ["CreatingApplication", component.CreatingApplication],
                ["Density", component.Density],
                ["Description", component.Description],
                ["DocumentNumber", component.DocumentNumber],
                ["EngineeringApprovalDate", component.EngineeringApprovalDate],
                ["EngineeringApprovedBy", component.EngineeringApprovedBy],
                ["EstimatedCost", component.EstimatedCost],
                # I am NOT including FileName, since it's an absolute file path
                # I would not personally want an automated export script revealing details about the structure of my filesystem in a public-facing Git repo
                ["Keywords", component.Keywords],
                ["LastAuthor", component.LastAuthor],
                ["LastUpdateDate", component.LastUpdateDate],
                ["ManufacturingApprovedBy", component.ManufacturingApprovedBy],
                ["ModifiedInformation", component.ModifiedInformation],
                ["Name", component.Name],
                ["Number", component.Number],
                ["Product", component.Product],
                ["ReceivedFrom", component.ReceivedFrom],
                ["Revision", component.Revision],
                ["StockSize", component.StockSize],
                ["Supplier", component.Supplier],
                ["Title", component.Title],
                ["Vendor", component.Vendor],
                ["WebLink", component.WebLink]
            ]

            writer.writerows(data)
    
    def _export_parameters_to_csv(self, component, export_path_abs):
        """Given a single Part or Assembly, export its Parameters to a CSV file at a specified path."""
        # type: (AlibreNeutralizer, Part | Assembly, str) -> None
        
        # If you don't put "wb" here, it puts an extra blank row between every row
        with open(export_path_abs, 'wb') as csv_file:
            writer = csv.writer(csv_file)

            # File header
            # This roughly mirrors the "Equation Editor" table view in Alibre's GUI
            writer.writerow(["Name", "Equation", "Value", "Units", "Type", "Comment"])

            for param in component.Parameters:
                writer.writerow([param.Name, param.Equation, param.Value, param.Units, param.Type, param.Comment])
            


def main():
    """This is the entry point of the program.
    Even though you don't HAVE to use a main function in Python scripts, I prefer it
    since it limits the scope of the variables inside this function."""

    window_name = "Alibre Neutralizer"
    
    # Take user input (ask for a config file)
    cfg_file_path = Windows().OpenFileDialog("Select Neutralizer Config File", "XML Files | *.XML", ".XML")
    # First see if they even selected anything
    if cfg_file_path == "" or cfg_file_path == None:
        # The user cancelled. Show an error to ensure they know what they just did.
        Windows().ErrorDialog("No config file was selected! Alibre Neutralizer will close now, and nothing will be exported.", window_name)

    # Create an instance using configuration from XML file
    neutralizer = AlibreNeutralizer(CurrentAssembly(), cfg_file_path)

    # Now that we've created an AlibreNeutralizer, give the user a quick summary of how we understood the config file
    # This is their last opportunity to cancel
    continue_window_prompt = """
    Successfully read the config file, which contains {edirs} export directives.

    Would you like to start Alibre Neutralizer's export process, following that configuration?
    
    THIS MAY DELETE FILES, if you've enabled the pre-export purge option on any of your export directives.
    """.format(edirs=len(neutralizer.export_directives))
    continue_choice = Windows().QuestionDialog(
        continue_window_prompt,
        window_name
    )

    # If the user said yes, go
    if continue_choice == True:
        neutralizer.export_all()
        Windows().InfoDialog("The export process completed!", window_name)
    else:
        Windows().InfoDialog("The export operation was cancelled. No files were modified. Alibre Neutralizer will now close.", window_name)

# Start main
main()

