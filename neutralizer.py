# import for auto-completion/code hints in development
from AlibreScript import *

# real dependencies
import os
import re

class ExportTypes:
    """AlibreScript's IronPython interpreter doesn't have the Enum library available, so this was my best shot at fudging enum-ish behavior."""
    STEP203 = 1
    STEP214 = 2
    SAT = 3
    STL = 4
    IGES = 5

    def get_file_extensions(self, export_type):
        """Given an integer representing an export file type, return a list of possible file extensions corresponding to that export file type."""
        if (export_type == self.STEP203) or (export_type == self.STEP214):
            return ["stp", "step"]
        elif (export_type == self.SAT):
            return ["sat"]
        elif (export_type == self.STL):
            return ["stl"]
        elif (export_type == self.IGES):
            return ["iges", "igs"]
        else:
            raise Exception("Invalid export type provided.")

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

        :param purge_directory_before_export: Set to a relative path that you'd like purged of your selected export type (.stp, .sat, etc) before exporting.
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
    
    def getExportPath(self, component):
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
        path = self.export_rel_path_expression.format(
            Comment = component.Comment,
            CostCenter = component.CostCenter,
            CreatedBy = component.CreatedBy,
            CreatedDate = component.CreatedDate,
            CreatingApplication = component.CreatingApplication,
            Density = component.Density,
            Description = component.Description,
            DocumentNumber = component.DocumentNumber,
            EngineeringApprovalDate = component.EngineeringApprovalDate,
            EngineeringApprovedBy = component.EngineeringApprovedBy,
            EstimatedCost = component.EstimatedCost,
            FileName = component.FileName, # This is a goofy convention of the Alibre API. "FileName" is really the absolute path. "Name" is the name on its own.
            Keywords = component.Keywords,
            LastAuthor = component.LastAuthor,
            LastUpdateDate = component.LastUpdateDate,
            ManufacturingApprovedBy = component.ManufacturingApprovedBy,
            ModifiedInformation = component.ModifiedInformation,
            Name = component.Name,
            Number = component.Number, # Part number
            Product = component.Product,
            ReceivedFrom = component.ReceivedFrom,
            Revision = component.Revision,
            StockSize = component.StockSize,
            Supplier = component.Supplier,
            Title = component.Title,
            Vendor = component.Vendor,
            WebLink = component.WebLink,
        )

        return path

class AlibreNeutralizer:
    """Create an instance of this, with an Alibre Assembly passed in, to handle the backend logic of recursively exporting files."""

    def __init__(self, component, base_path, export_directives = None):
        # type: (AlibreNeutralizer, Assembly | AssembledSubAssembly, str, list[ExportDirective] | None) -> None
        """Create and configure an instance of AlibreNeutralizer, the top-level class for managing bulk exports.
        
        :type self: AlibreNeutralizer

        :param component: The top-level assembly that you want to recursively export.
        :type component: Assembly | AssembledSubAssembly

        :param base_path: The base directory in which to store exports. This should be a relative path, relative to the location of ``component`` on the filesystem.
        In the unlikely event that your use case requires it, you can make this an absolute path, although it is generally not recommended.

        :param export_directives: A list of ExportDirectives defining the types of exports you want to make, how the files should be named/organized, and other parameters.
        You can add additional ExportDirectives after creating the class.
        """

        # Store the root assembly or part, our main connection point to Alibre
        if isinstance(component, Assembly):
            self.root_component = component
        else:
            raise Exception("Cannot initialize AssemblyNeutralizer without a valid Alibre Assembly object.")
        
        # Make sure the base path exists
        self.base_path = os.path.normpath(base_path)
        
        # Validate and store the export directives
        self.export_directives = list()
        if export_directives != None:
            for edir in export_directives:
                if isinstance(edir, ExportDirective):
                    self.export_directives.append(edir)
                else:
                    # If there's something in the list that ISN'T an ExportDirective
                    raise Exception("Invalid object received. Expected an instance of ExportDirective.")
    
    def _convert_base_path_to_absolute(self):
        """Convert self.base_path to an absolute path, relative to the directory where self.root_component is.
        In the rare case that self.base_path is already absolute, just return it as-is."""
        # type: (AlibreNeutralizer) -> str

        if os.path.isabs(self.base_path):
            return self.base_path
        else:
            # It's not absolute. We need to make it absolute.
            root_assembly_dir = os.path.dirname(
                os.path.normpath(self.root_component.FileName)
            )
            return os.path.normpath(os.path.join(root_assembly_dir, self.base_path))
    
    def export_all(self):
        """Carry out the ExportDirectives in ``self.export_directives`` on the Part or Assembly in ``self.root_component.``"""

        processed_files = set() # This will be a set of file absolute paths that we've processed (run export directives against).
        # This ensures we only export each component once.
        # Even if the export directive says not to export anything for a given file, we still add that file to the "processed" list.
        # Note that we use absolute paths (e.g. C:\wherever\myThing.AD_PRT) over Alibre's .Name property, because .Name includes the instance ID (the "<37>" type thing) at the end, while the filename does not.
        # May need to change this in the future if we want to export directly from PDM instead of from a package, since FileName is None in PDM.

        # Step 1: Export parts in root assembly, and add those parts to the exported_files list
        processed_files = processed_files.union(
            self._export_parts(self.root_component, self.export_directives, processed_files)
        )

        # Step 2: Export subassemblies in root assembly (recursive)
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
            else:
                print "Skipping {name}, since we already processed it.".format(name=part.Name)

        return already_processed_files

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
        pass # TODO: write real code here :)


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
                abs_export_path = self._get_absolute_export_path(
                    export_directive.getExportPath(component)
                )
                print "Should export this Part {name} to {path}".format(name=component.Name, path=abs_export_path)
                self._export(
                    component,
                    export_directive.export_type,
                    abs_export_path
                )
            elif export_directive.export_subassemblies == True and isinstance(component, AssembledSubAssembly):
                # We need to export this Subassembly
                abs_export_path = self._get_absolute_export_path(
                    export_directive.getExportPath(component)
                )
                print "Should export this Subassembly {name} to {path}".format(name=component.Name, path=abs_export_path)
                self._export(
                    component,
                    export_directive.export_type,
                    abs_export_path
                )
            elif export_directive.export_root_assembly == True and isinstance(component, Assembly):
                # We need to export this root Assembly
                abs_export_path = self._get_absolute_export_path(
                    export_directive.getExportPath(component)
                )
                print "Should export this Assembly {name} to {path}".format(name=component.Name, path=abs_export_path)
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
        except:
            print "ERROR: There was a problem exporting {0}.".format(component.FileName)
    
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

foo = AlibreNeutralizer(
    CurrentAssembly(),
    "./",
    [
        ExportDirective(ExportTypes.STEP203, "{Number}_{Name}.stp"), # You can use relative paths, as long as all the folders exist already. Don't put a leading . or \\, just start the first relative folder name.
        ExportDirective(ExportTypes.STL, "{Number}_{Name}.stl")
    ]
)

# Test export path generation
foo._execute_single_export_directive(CurrentAssembly(), foo.export_directives[0])
foo.export_all()

