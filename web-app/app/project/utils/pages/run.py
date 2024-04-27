"""
these functions used by the "Run" page of the website
and the associated routes in the views.py file
"""
from shutil import copy2
from pathlib import Path
import project.settings as settings
from project.utils.configure import configure_redis
from project.utils.Run.setupRun import SetupRun
from project.utils.Run.executeRun import ExecuteRun
from project.utils.utils import copy_config_files_from_template_dir_to_workbench


def start_run(formData) -> dict:
    run = SetupRun(formData)
    msgToClient = run.start_run()
    return msgToClient

def abort_run() -> dict:
    """
    abort the current run by aborting the celery task, which executes the clone detector tool containers
    """
    redis = configure_redis()
    
    runTaskID = redis.get('run.task.id')
    if runTaskID == None:
        return {'type': "error", 
                'message': "No run has been executed yet." }
    
    runIsRunning = redis.hget('run.progress', 'isExecuted')
    if runIsRunning == "False":
        return {'type': "error", 
                'message': "The current run can't be canceled, since no run is executed at the moment." }
    
    task = ExecuteRun().AsyncResult(runTaskID)
    task.abort()
    
    runID = redis.get("run.id")
    if runID == None:
        runID = ""
    
    return {'type': "success", 
            'message': f"Run {runID} canceled" }


def duplicate_tool_config(tool: str, newName: str) -> tuple[str, int]:
    """
    duplicate a detector tool's config file
    which results in one additional detector tool

    expected arguments:
        tool:  file name of the to be duplicated detector tool config file with web edit file extension, e.g.: NiCad.cfg.web.template
        newName: this name will be appended to the current tool's name in parentheses, e.g.:  tool="NiCad.cfg.web.template", newName="with some change" -> "NiCad (with some change).cfg.web.template"
    """
    # ensure there is no path in front of the tools file name
    tool    = Path(tool)
    tool    = Path(tool.name)

    confDir = Path(settings.directories["confWorkbench"])
    fileExtensionBase    = settings.templateFiles['fileExtensionBase']
    fileExtensionWebEdit = settings.templateFiles['fileExtensionWebEdit']

    if not confDir.joinpath(tool).is_file():
        return "Error: specified file does not exist", 400
    
    if not tool.name.endswith(fileExtensionWebEdit):
        return f"Error: invalid specified file. Expected web edit template file ({fileExtensionWebEdit})", 400

    # tool name without file extension
    tool = tool.name.rstrip(fileExtensionWebEdit)

    srcTemplate    = confDir / f"{tool}{fileExtensionBase}"
    newTemplate    = confDir / f"{tool} ({newName}){fileExtensionBase}"

    srcWebTemplate = confDir / f"{tool}{fileExtensionWebEdit}"
    newWebTemplate = confDir / f"{tool} ({newName}){fileExtensionWebEdit}"

    copy2(srcTemplate, newTemplate)
    copy2(srcWebTemplate, newWebTemplate)
        
    return "duplication successfull", 200


def reset_workbench_configs() -> None:
    """
    remove all duplicated tools and reset all tools to default by:
    1. removing all files in the workbench directory
    2. copy all template config files from the template directory to the workbench directory
    """
    confDir = settings.directories["confWorkbench"]

    # delete all files in the workbench directory
    for file in Path(confDir).glob("*"):
        file.unlink()

    copy_config_files_from_template_dir_to_workbench()

