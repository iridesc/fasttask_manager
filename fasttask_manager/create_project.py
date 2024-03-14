import os
import shutil


def get_int_input_or_default(name, default):
    input_str = input(f"{name} (default:{default}):")
    return int(input_str) if input_str else default


def read_file(file):
    with open(file) as f:
        return f.read()


def write_file(content, file):
    with open(file, "w") as f:
        f.write(content)


def replace_file_content(file, replace_dict):
    content = read_file(file)
    for k, v in replace_dict.items():
        content = content.replace("{" + k + "}", str(v))
    write_file(content, file)


def create_project():
    project_name = input("project name:")
    port = get_int_input_or_default("port", 80)
    fasttask_path = os.path.abspath(os.path.dirname(__file__))

    shutil.copytree(os.path.join(fasttask_path, "project"), f"{project_name}")

    replace_dict = {"project_name": project_name, "port": port}

    replace_file_content(f"{project_name}/docker-compose.yml", replace_dict)
    replace_file_content(f"{project_name}/setting.py", replace_dict)


if __name__ == "__main__":
    create_project()
