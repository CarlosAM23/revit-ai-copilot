# context.py
# This module extracts data from the active Revit model
# and formats it as a text summary to send to the AI

from pyrevit import revit
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory
)

def get_model_context():
    """
    Extract key data from the active Revit model.
    Returns a formatted string to inject into the AI system prompt.
    """
    doc = revit.doc

    # Get project name from document title
    project_name = doc.Title

    # Get active view name and type
    active_view = doc.ActiveView
    view_name = active_view.Name
    view_type = active_view.ViewType.ToString()

    # Count elements by category
    def count_category(category):
        return FilteredElementCollector(doc)\
            .OfCategory(category)\
            .WhereElementIsNotElementType()\
            .GetElementCount()

    doors   = count_category(BuiltInCategory.OST_Doors)
    walls   = count_category(BuiltInCategory.OST_Walls)
    windows = count_category(BuiltInCategory.OST_Windows)
    rooms   = count_category(BuiltInCategory.OST_Rooms)
    floors  = count_category(BuiltInCategory.OST_Floors)

    # Get all level names
    levels = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Levels)\
        .WhereElementIsNotElementType()\
        .ToElements()
    level_names = ", ".join([l.Name for l in levels])

    # Format everything as a structured text block
    context = """
PROJECT CONTEXT:
- Project name: {project}
- Active view: {view} ({vtype})
- Levels: {levels}

MODEL SUMMARY:
- Walls: {walls}
- Doors: {doors}
- Windows: {windows}
- Rooms: {rooms}
- Floors: {floors}
""".format(
        project = project_name,
        view    = view_name,
        vtype   = view_type,
        levels  = level_names,
        walls   = walls,
        doors   = doors,
        windows = windows,
        rooms   = rooms,
        floors  = floors
    )

    return context


def get_selected_element_context():
    """
    Read parameters from the currently selected element in Revit.
    Returns a formatted string with all relevant parameters.
    If nothing is selected, returns empty string.
    """
    doc = revit.doc
    uidoc = revit.uidoc

    # Get current selection from Revit UI
    selection = uidoc.Selection.GetElementIds()

    # If nothing is selected return empty string
    if selection.Count == 0:
        return ""

    # Read first selected element only
    element_id = list(selection)[0]
    element = doc.GetElement(element_id)

    if not element:
        return ""

    def safe_str(value):
        """Convert any value to ASCII-safe string."""
        try:
            text = str(value)
            return text.encode('ascii', 'ignore').decode('ascii').strip()
        except:
            return ""

    # Get basic element info safely
    try:
        category = safe_str(element.Category.Name) if element.Category else "Unknown"
    except:
        category = "Unknown"

    try:
        element_id_str = str(element.Id.Value)
    except:
        try:
            element_id_str = str(element.Id.IntegerValue)
        except:
            element_id_str = "Unknown"

    try:
        from Autodesk.Revit.DB import BuiltInParameter
        family_param = element.get_Parameter(BuiltInParameter.ELEM_FAMILY_PARAM)
        family_name = safe_str(family_param.AsValueString()) if family_param else "Unknown"
    except:
        family_name = "Unknown"

    try:
        from Autodesk.Revit.DB import BuiltInParameter
        type_param = element.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM)
        type_name = safe_str(type_param.AsValueString()) if type_param else "Unknown"
    except:
        type_name = "Unknown"

    try:
        from Autodesk.Revit.DB import BuiltInParameter
        level_param = element.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM)
        level_name = safe_str(level_param.AsValueString()) if level_param else "N/A"
    except:
        level_name = "N/A"

    # Read all instance parameters safely with unit conversion
    params_text = ""
    for param in element.Parameters:
        try:
            param_name = safe_str(param.Definition.Name)
            storage = param.StorageType.ToString()

            if storage == "String":
                raw = param.AsString()
                param_value = safe_str(raw) if raw else ""
            elif storage == "Double":
                # Convert from Revit internal units (feet) to millimeters
                raw_value = param.AsDouble()
                mm_value = round(raw_value * 304.8, 2)
                param_value = safe_str(mm_value) + " mm"
            elif storage == "Integer":
                param_value = safe_str(param.AsInteger())
            elif storage == "ElementId":
                try:
                    param_value = safe_str(param.AsElementId().Value)
                except:
                    param_value = safe_str(param.AsElementId().IntegerValue)
            else:
                param_value = ""

            # Only include parameters with meaningful values
            if param_name and param_value and param_value not in ["-1", "0", "None", "", "0.0 mm"]:
                params_text += "  - {}: {}\n".format(param_name, param_value)
        except:
            pass

    element_context = """
SELECTED ELEMENT:
- Category: {}
- Element ID: {}
- Family: {}
- Type: {}
- Level: {}

ELEMENT PARAMETERS:
{}
""".format(
        category,
        element_id_str,
        family_name,
        type_name,
        level_name,
        params_text if params_text else "  No parameters found"
    )

    return element_context