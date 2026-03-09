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