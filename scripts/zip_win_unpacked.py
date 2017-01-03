import math
import os
import time
import zipfile


script_tag = "[OT App Zip] "
script_tab = "             "


project_root_dir = \
    os.path.dirname(                                  # going up 1 level
        os.path.dirname(os.path.realpath(__file__)))  # folder dir of this

electron_app_dir = os.path.join(project_root_dir, "")


dir_to_zip = "C:\\projects\\opentrons-app\\dist\\win-unpacked"


def zip_ot_app(build_tag):
    print(script_tab + "Zipping OT App. Using tag: {}".format(build_tag))

    # Assuming there is only one app in the electron build dir, zip that app
    current_app_name = 'ot-app'
    current_app_path = dir_to_zip

    # We need to CD into the directory where the Mac app executable is located
    # in order to zip the files within that directory and avoid zipping that
    # directory itself
    old_cwd = os.getcwd()
    os.chdir(current_app_path)

    print(script_tab + "Zipping {} located in {}".format(
        current_app_name, os.getcwd())
    )

    releases_dir = os.path.join(project_root_dir, 'releases')
    if not os.path.isdir(releases_dir):
        os.mkdir(releases_dir)

    # Place app in the releases dir
    # e.g. <project root>/releases/opentrons_<build tag>.zip
    zip_app_path = os.path.join(
        releases_dir,
        "opentrons_{}.zip_z".format(build_tag)
    )
    print(script_tab + "Zipped application will be located in: {}".format(
        zip_app_path
    ))

    zip_output = zipfile.ZipFile(zip_app_path, 'w', zipfile.ZIP_DEFLATED)
    for dirname, subdirs, subfiles in os.walk('.'):
        zip_output.write(dirname)
        for filename in subfiles:
            zip_output.write(os.path.join(dirname, filename))
    zip_output.close()


if __name__ == "__main__":
    zip_ot_app(str(math.floor(time.time())))
