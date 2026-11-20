# 05 · OpenUI Lang: a compact language for generated UI

OpenUI Lang ([openui.com](https://www.openui.com/)) describes an interface as a short program instead of a JSON document. One statement per line:

```text
root = Stack([title, plan])
title = Text("Spring 2027 · suggested plan", "h1")
plan = Table(["Course", "When"], rows)
rows = [["CMPE 280", "Mon/Wed 18:00"], ["CMPE 281", "Tue/Thu 18:00"]]
```

* Expressions are strings, numbers, booleans, `null`, arrays, references to other names, and component calls with **positional** arguments. The catalog defines each component's parameter order.
* A reference may point **forward** to a line that has not arrived yet. While streaming, it renders as a placeholder.
* Assigning a name again **replaces** it. An update is just a few new lines.
* There are no property names and few brackets, so a program is shorter than the same UI in JSON.

`openui.py` and `openui.mjs` are a tokenizer, a parser, a resolver and a renderer written for these codelabs, with matching behaviour in Python (server checks, tests) and JavaScript (streaming render in the page).

## The four codelabs

| Mode | Codelab | Components the model may call | Update path |
|---|---|---|---|
| static | [1_static](1_static/README.md) | three pre-built widgets: `CourseList`, `CourseCard`, `ConflictAlert` | server code re-assigns two names |
| declarative | [2_declarative](2_declarative/README.md) | the primitives (`Stack`, `Card`, `Text`, `Metric`, `Table`, ...) | the model re-assigns four names |
| open-ended | [3_open_ended](3_open_ended/README.md) | only `HtmlArtifact(html, title, height)` | a new `root` |
| mixed | [4_mixed](4_mixed/README.md) | primitives plus at most one `HtmlArtifact` | the model re-assigns five names, including the artifact |

The scenario is planning a spring semester.

## The shared code

`openui.py`, the grammar in one regular expression and a recursive parser:

```python
TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|(?P<id>[A-Za-z_]\w*)|(?P<p>[=(),\[\]]))')
```

```python
        statements[name] = expr                      # a later assignment replaces an earlier one
```

`openui.mjs`, forward references while resolving:

```js
      case "ref":
        if (seen.has(expr[1]) || !statements.has(expr[1])) return { type: "_pending", name: expr[1] };
```

`client.mjs` re-parses after each *completed* line and repaints only when a new line has finished:

```js
    const complete = partial ? program.slice(0, program.lastIndexOf("\n") + 1) : program;
```

## Run

```bash
python -m pytest -q 05_openui_lang
```

```bash
python run_all.py 05_openui_lang
```
