import json
from jinja2 import Environment, Template
import os

def jinja2_template(source):
    def json_helper(items):
        result = ['\n~~~JSON\n']
        result.append(json.dumps(items, indent=2))
        result.append('\n~~~\n')
        return ''.join(result)

    env = Environment()
    env.filters['json'] = json_helper
    template = env.from_string(source)

    async def apply(case):
        return template.render(**case)

    return apply

def load_template(filename):
    #
    # Read the template file
    #
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Template file {filename} does not exist.")
    try:
        with open(filename, "r") as file:
            template_text = file.read()
    except Exception as e:
        raise ValueError(f"Error reading template file {filename}: {e}")

    #
    # Compile the template
    #
    try:
        template = jinja2_template(template_text)
    except Exception as e:
        raise ValueError(f"Error compiling template: {e}")

    return (template_text, template)
