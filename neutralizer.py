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

class ExportDirective:
    """Each instance of this directs AssemblyNeutralizer to export a particular type of file, with a particular relative path and filename.
    For example, a STEP214 export to ./whatever/relative/path/{FileName}_{Revision}.stp ."""

    def __init__(self, export_type, export_rel_path_expression, export_root_assembly=True, export_subassemblies=True, export_parts=True):
        # type: (ExportDirective, int, str, bool, bool, bool) -> None
        """
        Define a new Export Directive. You'll need one of these for each type of file you want to export.

        :param export_type: Specify a single file type for this export. See the ExportTypes "static" class for options.
        :type export_type: str

        :param export_rel_path_expression: Specify a formula for the relative path of each exported file, using Python string .format syntax.
        For example, ``./whatever/relative/path/{FileName}_{Revision}.stp``. Available variables are: TODO
        :type export_rel_path_expression: str

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

        # Store data on which types of components we should export
        self.export_root_assembly = export_root_assembly
        self.export_subassemblies = export_subassemblies
        self.export_parts = export_parts
    
    def getExportPath(self, component):
        """Given a Part or Subassembly or Assembly, return the relative Export path based on the expression in ``export_rel_path_expression``.
        
        :type self: ExportDirective

        :param component: The component (Part or Assembly) whose export path you want to evaluate.
        :type component: Assembly | Part | Subassembly
        """
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
        # type: (AlibreNeutralizer, Assembly | Part, str, list[ExportDirective] | None) -> None

        # Store the root assembly or part, our main connection point to Alibre
        if isinstance(component, Assembly):
            self.root_component = component
        else:
            raise Exception("Cannot initialize AssemblyNeutralizer without a valid Alibre Assembly object.")
        
        # Make sure the base path exists
        if not os.path.exists(base_path):
            raise Exception("Provided Base Path does not exist! We will be unable to export there.")
        else:
            # if it does exist, store it
            self.base_path = base_path
        
        # Validate and store the export directives
        self.export_directives = list()
        if export_directives != None:
            for edir in export_directives:
                if isinstance(edir, ExportDirective):
                    self.export_directives.append(edir)
                else:
                    # If there's something in the list that ISN'T an ExportDirective
                    raise Exception("Invalid object received. Expected an instance of ExportDirective.")
    
    def export_all(self):
        """Carry out the ExportDirectives in ``self.export_directives`` on the Part or Assembly in ``self.root_component.``"""

        exported_files = set() # This will be a set of filenames that we've exported. This ensures we only export each component once.

        # Step 1: Export parts in root assembly, and add those parts to the exported_files list
        exported_files = exported_files.union(
            self._export_parts(self.root_component, self.export_directives, exported_files)
        )

        # Step 2: Export subassemblies in root assembly (recursive)
        # for subassy in subassemblies
        #   for edir in export_directives
        #     newly_exported_names = _export_subassembly_recursive(component, edir)
        #     exported_files.append(newly_exported_names)

    def _export_parts(self, assembly, export_directives, already_exported_files):
        """Given an Assembly (or AssembledSubAssembly), an ExportDirective, and a list of already-exported files to ignore,
        export the parts in the assembly according to the ExportDirective, and return an updated list of exported files."""
        # type (AlibreNeutralizer, Assembly | AssembledSubAssembly, list[ExportDirective], set[str]) -> set[str]

        newly_exported_files = list()
        for part in assembly.Parts:
            # Run through all the export directives on this part
            for edir in export_directives:
                self._execute_single_export_directive(part, edir)
            # Once all Export Directives have been executed, add it to the list of exports
            newly_exported_files.append(part.Name)

        return already_exported_files.union(newly_exported_files)
        
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
    
    def _get_absolute_export_path(self, export_path_relative):
        """Combine a given relative export path with this ``AlibreNeutralizer``'s absolute ``base_path``, to give an absolute path."""
        probable_path = os.path.join(self.base_path, export_path_relative)

        # Scrub out some illegal characters
        pattern = r'[^\w_.: \-' + re.escape(os.sep) + r']'
        probable_path = re.sub(pattern, '_', probable_path)

        # TODO: still could use more error checking
        return probable_path

foo = AlibreNeutralizer(
    CurrentAssembly(),
    "D:\\Users\\Hampton\\Downloads\\TestNeutralizer",
    [
        ExportDirective(ExportTypes.STEP203, "{Name}.stp"), # You can use relative paths, as long as all the folders exist already. Don't put a leading . or \\, just start the first relative folder name.
        ExportDirective(ExportTypes.STL, "./whatever/the/path/is.stl")
    ]
)

# Test export path generation
foo._execute_single_export_directive(CurrentAssembly(), foo.export_directives[0])
foo.export_all()

