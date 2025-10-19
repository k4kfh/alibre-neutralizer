from AlibreScript import *

# export a single part or assembly to STEP, at a given file path
def exportToSTEP(component, file_path):
  # Eventually, wrap this in some kind of code that throws an exception when it "times out"
  component.ExportSTEP214(file_path + '.stp')

# isolate the actual file NAME. Alibre's Part.FileName and Assembly.FileName are really the absolute path.
# e.g. for "C:\Wherever\MyWidget.AD_ASM", this will return "MyWidget"
def isolateComponentName(component):
  return component.FileName.split('/')[-1].rsplit('.', 1)[0]

# Generic helper function for exporting a part or an assembly to a specific target folder, with an optional suffix
def exportComponent(component, target_folder, file_suffix = None):
  isolated_filename = isolateComponentName(component)
  if file_suffix == None:
    file_suffix = ""
  
  export_path_absolute = None # Define this here, just so it's scoped appropriately

  # For now, I want to hardcode in the part number to all the file names (unless the part number isn't set).
  # The part number seems to default to the component name, or empty. So if it's either of those values, don't include it in the filename.
  if (component.Number != "") and (component.Number != isolated_filename):
    # We want to include the P/N (myThing.Number) in the file name
    export_path_absolute = target_folder + '\\' + component.Number + "_" + isolated_filename + file_suffix
  else:
    # It doesn't appear P/N (myThing.Number) is set to a meaningful value, so let's don't include it in the file name
    export_path_absolute = target_folder + '\\' + isolated_filename + file_suffix
  exportToSTEP(component, export_path_absolute)

# Export a list of Parts into a given target folder, with an optional suffix applied to each file's name.
# Return a deduplicated list of all the files exported.
def exportParts(parts, target_folder, file_suffix = None, exported_files = None):
  # Keep a local list of all the files we export.
  # The caller can "preload" this list with previously exported files (their absolute paths) if needed.
  if exported_files == None:
    exported_files = set()

  # Export all parts
  for part in parts:
    # This keeps us from exporting multiple occurrences of the same part
    if part.FileName not in exported_files:
      # part.FileName is really the absolute path, not just the file name. So we need to isolate the file name.
      print "Exporting {0}, P/N {1}...".format(isolateComponentName(part), part.Number)
      exportComponent(part, target_folder, file_suffix)
      exported_files.add(part.FileName)
    else:
      print "Skipped exporting duplicate occurrence of {0}".format(isolateComponentName(part))
  
  return exported_files

# recursive function to walk tree of subassemblies
def exportSubassemblyPartsRecursive(subassembly, target_folder, file_suffix=None, exported_files = None, export_parts_only=True):
  # Export the parts at this assembly level
  parts = subassembly.Parts
  if len(parts) > 0:
    exported_files = exported_files.union(exportParts(parts, target_folder=target_folder, file_suffix=file_suffix))


  # Did the caller ask to export STEPs of the subassemblies as well (export_parts_only=False)?
  if (export_parts_only == False):
    exportComponent(subassembly, target_folder, file_suffix)
    exported_files.add(subassembly.FileName)
  
  # Does it have any subassemblies? If, so recurse into them
  subs =  subassembly.SubAssemblies
  if len(subs) > 0:
   for sub in subs:
   # recursion here
    exported_files = exported_files.union(exportSubassemblyPartsRecursive(sub, target_folder, file_suffix, exported_files, export_parts_only))
  
  return exported_files

# Encapsulate the business logic in a "main" function, just to keep from having to create global variables
def main():
  # create windows object
  Win = Windows()

  assem = CurrentAssembly()

  #default_folder = 'c\\Users\\Joe Sacher\\OneDrive\\Alibre\\Spice Rack\\'
  # TODO: Pick the default folder intelligently so you have a structure like:
  # - ./L
  # - ./P
  # - ./STEPs
  # - ./STLs
  # ...etc
  # Probably the best way to do this is check every folder in the path and see if there's a MyWidget.AD_PKG, where MyWidget is the name of the current assembly.
  default_folder = ''

  # construct list of items for the window
  Options = []
  # ask user for text
  Options.append(['Export Folder', WindowsInputTypes.Folder, default_folder])
  # filename suffix
  Options.append(['Filename Suffix', WindowsInputTypes.String, ''])
  # export types
  export_types = ["STEP", "STL"]
  Options.append(['Export type', WindowsInputTypes.StringList, export_types])
 
  # show window and output results
  # if user closes window or clicks on Cancel button then Values will be set to 'None'
  Values = Win.OptionsDialog('Export All Models', Options)
  if Values is None:
    exit()
  target_folder, suffix, export_type_index = Values

  # First, export parts at the top assembly level.
  # Store the list of exported parts so we can de-duplicate future exports.
  print "Exporting top-level parts..."
  exported_files = exportParts(assem.Parts, target_folder=target_folder, file_suffix=suffix)

  # Then, if there are any subassemblies, recurse through them and export the parts in each one.
  # Pass in the existing exported_files list, so we can skip anything we've already exported.
  print "Recursing through subassemblies..."
  if len(assem.SubAssemblies) > 0:
    for sub in assem.SubAssemblies:
      exported_files = exported_files.union(exportSubassemblyPartsRecursive(sub, target_folder=target_folder, file_suffix=suffix, exported_files=exported_files, export_parts_only=False))
  
  print "Successfully exported {0} components.".format(len(exported_files))

# Call our faux main function
main()

