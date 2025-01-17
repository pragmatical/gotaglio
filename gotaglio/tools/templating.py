# import asyncio
import json
from jinja2 import Environment, Template

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

# async def go():
#     template_text = "Hello, {{ name }}!"
#     template = jinja2_template(template_text)
#     context = {"name": "Mike"}
#     template = jinja2_template(template_text)
#     result = await template(context)
#     print(result)

# asyncio.run(go())

