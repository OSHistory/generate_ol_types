"""
Iterate all temporary declaration files and 
make some quick fixes to create some basic 
functionality 
    - remove .js from imports
    - transform @typedef comments to interfaces
    - transform opt_ to optional declaration in constructor
    - misc fixes
"""

import json
import os
import re 

def fix_imports(content):
    all_imports = collect_imports(content)
    for _import in all_imports: 
        content = content.replace(_import, _import.replace(".js'", "'"))
    return content

def no_never_returns(content):
    return content.replace(": never", ": any")

def no_this_returns(content):
    return content.replace(": this", ": any")

def mark_optional(content):
    optional_args = re.findall("opt_[a-zA-Z]*?:", content)
    optional_args = list(set(optional_args))
    for arg in optional_args:
        new_arg = arg.replace("opt_", "").replace(":", "?:")
        if new_arg == "this?:":
            new_arg = "_this?:"
        content = content.replace(arg, new_arg)
    return content

"""
transforms (Array<number>, any, number) into 
(param1: Array<number>, param2: any, param3: number)
"""
def generate_anomymous_param_names(fun_part):
    param_str = fun_part.strip()[1:-1]
    params = param_str.split(",")
    if params[0] == "":
        return fun_part
    print(params)
    # TODO: this: ? (e.g. condition.d.ts)
    out_params = []
    for idx, param in enumerate(params):
        out_param = "param" + str(idx)
        # TODO: how to handle ! (cast to any for now)
        if param.startswith("!"):
            param = "any"
        # TODO: Use of ? before function param (e.g. PluggableMap), remove for now
        if param.startswith("?"):
            param = param[1:]
        if param.endswith("="):
            param = param[:-1]
            out_param += "?"
        out_param += ": " + param
        out_params.append(out_param)
    # out_params = ["param" + str(idx) + ": " + param for idx, param in enumerate(params)]
    print(out_params)
    return "({params})".format(params=", ".join(out_params))

def transform_function_def(fun_def):
    print("FUnction transform")
    print(fun_def)
    if "this:" in fun_def:
        print("WEIRD THIS")
        print(fun_def)
    fun_def = fun_def.replace("*", "any")
    # TODO: optional self referal? cast to any for the moment
    fun_def = fun_def.replace("this: ?", "any")
    fun_def = fun_def.replace("this:", "")
    fun_def = re.sub("^function", "", fun_def)
    if ":" in fun_def:
        fun_parts = fun_def.rpartition(":")
        out_fun = generate_anomymous_param_names(fun_parts[0]) + " => " + fun_parts[2]
    else:
        out_fun = generate_anomymous_param_names(fun_def) + " => void"

    # if out_fun.strip().startswith("=>"):
    #     out_fun = "() " + out_fun.strip()
    print(out_fun)
    return out_fun 

"""
Iterate over a string and return 
the content between the first 
parenthesis and its closing counterpart
"""
def extract_bracket_content(content, bracket_type_open, bracket_type_close):
    out_content = ""
    bracket_count = 0
    record = False
    for char in content:
        if char == bracket_type_open:
            record = True
            bracket_count += 1
        elif char == bracket_type_close:
            bracket_count -= 1
        if record:
            out_content += char
        if record and bracket_count == 0:
            break
    return out_content            

"""
Splits a doc line into 
ts_type ({})
ol_name ([])
description (the rest)
"""
def parse_property_line(doc_line):
    # replacements for special cases 
    print("PARSING PROPERTY")
    print("DOC_LINE")
    print(doc_line)
    ts_type = extract_bracket_content(doc_line, "{", "}")
    doc_rest = doc_line.partition(ts_type)[2].strip()
    # do not split by space as the OL-name part 
    # could be something like [tileSize=256, 256]
    ts_type = ts_type[1:-1]
    if ts_type.strip() in ["?", "*"]:
        ts_type = "any"
    if ts_type.startswith("!"):
        ts_type = ts_type[1:]
    # doc_line.partition("{")[2].rpartition("}")[0] 
    if ".js" in ts_type:
        ts_type = ts_type.replace(".js", "")
    if ts_type.startswith("function"):
        ts_type = transform_function_def(ts_type)
    print("TS")
    print(ts_type)
    print("DOC_REST")
    print(doc_rest)
    # parse the rest of the string
    if doc_rest.startswith("["):
        first_word = extract_bracket_content(doc_rest, "[", "]")
        first_word = first_word[1:-1]
    else:
        first_word = doc_rest.partition(" ")[0].strip()
    print("FIRST WORD")
    print(first_word)
    description = doc_rest.replace(first_word, "").strip()
    print(doc_rest)

    # # first word assumed to be OL-name (either with or without [])
    # first_word = doc_rest.partition(" ")[0].strip()
    # print("FIRST")
    # print(first_word)
    # if first_word.startswith("[") and first_word.endswith("]"):
    #     first_word = first_word[1:-1]
    # Split of default value
    first_word = first_word.split("=")[0]
    # print(first_word)
    # description = doc_rest.partition(" ")[2]
    # try: 
    #     ol_name = re.split("[\[\]]", doc_line)[1]
    #     ol_name = ol_name.split("=")[0].strip()
    #     description = doc_line.rpartition("]")[2]
    # # in case no brackets provided with source, use first word as olName 
    # except:
    #     # print("EXCEPT")
    #     # print(doc_line)
    #     text = doc_line.partition("}")[2].strip()
    #     ol_name = text.split(" ")[0].strip()
    #     description = " ".join(text.split(" ")[1:])
    description = re.sub("[\*/]", "", description)
    print("PARSED_PROPERTY")
    print({
        "tsType": ts_type, 
        "olName": first_word, 
        "description": description
    })
    return {
        "tsType": ts_type, 
        "olName": first_word, 
        "description": description
    }

def parse_typedef_line(type_line):
    # _type = type_line.partition("{")[2].rpartition("}")[0]
    _type = extract_bracket_content(type_line, "{", "}")
    _type = _type[1:-1]
    if _type.startswith("function"):
        _type = transform_function_def(_type)
    if _type.startswith("!"):
        _type = _type[1:]
    name = type_line.rpartition("}")[2].strip().split(" ")[0].strip()

    return {
        "type": _type,
        "name": name
    }


"""
Finds all @typedef comments and creates interfaces 
"""
def typedef_to_interface(content, ts_import_dict, js_import_dict):
    interfaces = []
    interface_names = []
    types = []
    type_names = []
    imports = []
    content = re.sub("/\*\*.*?@module.*?\*/", "", content, flags=re.DOTALL)
    typedefs = re.findall("/\*\*.*?@typedef.*?\*/", content, re.DOTALL)
    for typedef in typedefs:
        if "@module" in typedef:
            continue
        typedef_line = re.search("@typedef[^@]*", typedef).group()
        # remove comments for multiliners
        typedef_line = re.sub("\n *\*/?", "", typedef_line, re.DOTALL)
        typedef_obj = parse_typedef_line(typedef_line)
        # no properties -> create simple type 
        if not "@property" in typedef:
            type_declaration = "\nexport declare type {name} = {_type};\n".format(
                name=typedef_obj["name"],
                _type=typedef_obj["type"]
            )
            # keep original comment
            type_declaration = typedef + type_declaration
            types.append(type_declaration)
            type_names.append(typedef_obj["name"])
        # parse properties and create an interface
        else:
            interface_str = """\nexport interface {typeName} {{\n""".format(
                typeName=typedef_obj['name']
            )
            property_lines = typedef.split("@property")
            for prop_line in property_lines[1:]:
                prop_obj = parse_property_line(prop_line)
                # check if tsType is in either one of the import dictionnaries
                # add to imports if not present
                ts_type = prop_obj["tsType"]
                sub_types = ts_type.split("|")
                print(sub_types)
                for sub_type in sub_types:
                    print("SUB_TYPE")
                    print(sub_type)
                    # could be a generic
                    sub_type = sub_type.partition("<")[0]
                    print(sub_type)
                if  sub_type not in ts_import_dict and sub_type in js_import_dict:
                    print("OOPS, better import it!")
                    path = js_import_dict[sub_type].replace(".js", "")
                    ts_import_dict[sub_type] = path
                    imports.append("import {type} from {path};".format(type=sub_type, path=path))
                if prop_obj['olName'] != '':
                    interface_str += """  /** {description} */\n  {olName}?: {tsType};\n""".format(
                        description=prop_obj["description"],
                        tsType=prop_obj["tsType"],
                        olName=prop_obj["olName"]
                    )
            interface_str += "\n}\n"
            interfaces.append(interface_str)
            interface_names.append(typedef_obj['name'])
    return interfaces, interface_names, types, type_names, imports

def collect_imports(content):
    return re.findall("^import.*?from '.*?';", content, re.MULTILINE)

def add_after_import(content, add_cont):
    imports = collect_imports(content)
    if len(imports):
        last_import = imports[len(imports)-1]
        content = content.replace(last_import, last_import + add_cont)
    else: 
        content = add_cont + content
    return content

def use_typed_options_in_constructor(content, has_own_object, import_object):
    # get the class declaration including constructor
    # and extract the @param declaration
    class_declarations = re.findall("declare class.*?constructor\(.*?\)", content, re.DOTALL)
    for class_declaration in class_declarations:
        try:
            parameter = re.search("@param.*", class_declaration).group()
        except:
            continue
        param_content = re.split("[{}]", parameter)[1]

        # Only apply to options
        if not "constructor(options" in class_declaration:
            continue 

        # If simple options specified, the interface is 
        # present in the declaration itself
        # or exported from the extended class
        optional = param_content.endswith("=")
        if optional:
            param_content = param_content[:-1]
        if param_content.startswith("!"):
            param_content = param_content[1:]
        # TODO: unnecessary
        # resolve import
        if param_content.startswith("import("):
            import_path = param_content.split('"')[1].replace(".js", "")
            import_name = import_path.rpartition("/")[2]
            type_name = param_content.rpartition(".")[2]
            if (type_name == 'default'):
                type_name = import_name
            if optional:
                content = content.replace("constructor(options?: any", "constructor(options?: " + type_name)
            else:
                content = content.replace("constructor(options: any", "constructor(options: " + type_name)            
            new_import = "import {" + type_name + "} from '" + import_path + "';\n"
            imports = collect_imports(content)
            if len(imports):
                content = content.replace(imports[0], imports[0] + "\n" + new_import)
            else:
                content = new_import + "\n" + content
        # no external import (assume same class or extending)
        else:
            # if extending class and no Object type definition in 
            # the class itself, add an import 
            # (for example TileLayer extends BaseTileLayer)
            extends = "extends" in class_declaration
            if extends and not has_own_object:
                declare_statement = re.search("declare class.*", class_declaration).group()
                base_class = declare_statement.split(" ")[4]
                import_statement = "\nimport { Options } from " + import_dict[base_class] + ";"
                imports = collect_imports(content)
                if len(imports):
                    last_import = imports[len(imports)-1]
                    content = content.replace(last_import, last_import + import_statement)
                else: 
                    content = import_statement + "\n" + content

            if optional:
                content = content.replace("constructor(options?: any", "constructor(options?: " + param_content)
            else:
                content = content.replace("constructor(options: any", "constructor(options: " + param_content)
    return content 

def generate_import_dict(content):
    import_dict = {}
    imports = collect_imports(content)
    for _import in imports:
        _import = re.sub("[{}]", "", _import)
        import_parts = _import.split(" ")
        import_dict[import_parts[1]] = import_parts[3].replace(";", "")
    return import_dict

"""
due to renaming opt to ?, duplicate identifiers can occur (e.g. in extent.d.ts)
"""
def fix_duplicate_params(content):
    fun_defs = re.findall("[a-zA-Z]*\([a-zA-Z]*?: [a-zA-Z].*?\)\: [a-zA-Z]*;", content)
    for fun_def in fun_defs:
        fun_split = re.split("[()]", fun_def)
        params_str = fun_split[1]
        params = params_str.split(",")
        param_names = [param.split(":")[0].replace("?", "").strip() for param in params]
        param_increment = {}
        for param_idx, param_name in enumerate(param_names):
            if param_names.count(param_name) > 1:
                if param_name not in param_increment:
                    param_increment[param_name] = 1
                else:
                    param_increment[param_name] += 1
                    # already present, rename original param
                    params[param_idx] = params[param_idx].replace(param_name, param_name + str(param_increment[param_name]))
        new_fun_def = fun_split[0] + "(" + ", ".join(params) + ")" + fun_split[2]
        content = content.replace(fun_def, new_fun_def)
    return content

def resolve_generics(content):
    generics = []
    class_declarations = re.findall("/\*\*.*?@classdesc.*?\*/[ \n]*?declare class [a-zA-Z]* ", content, re.DOTALL)
    for class_declaration in class_declarations:
        if "@template T" in class_declaration:
            last_line = class_declaration.rpartition("\n")[2]
            class_name = last_line.strip().rpartition(" ")[2]
            generics.append(class_name)
            content = content.replace(last_line, last_line.strip() + "<T> ")

    return content, generics

"""
replaces the falsely exported object as an enum
"""
def replace_const_default_export(content, enum_dict):
    declaration = re.search("declare const _default: {.*?};", content, re.DOTALL).group()
    out_declaration = "declare enum _default {\n"
    for key in enum_dict:
        out_declaration += "    {key} = {value},\n".format(key=key, value=enum_dict[key])
    out_declaration += "}"
    # new_declaration = declaration.replace(";", ",")
    # new_declaration = new_declaration.replace(":", "=")
    # new_declaration = new_declaration.replace(
    #     "declare const ", "declare enum ")
    # new_declaration = new_declaration.replace(" _default: ", " _default ")
    print("REWRITE ENUM")
    print(declaration)
    print(out_declaration)
    content = content.replace(declaration, out_declaration)
    return content

def create_enum_dict(js_content):
    enum_dict = {}
    print("ENUM_DICT")
    print(js_content)
    # might have comments (e.g. Tilestate), use 
    #     
    export = js_content.partition("export default {")[2]
    export = export.replace("};", "").strip()
    print(export)
    export = re.sub("/\*\*.*?\*/", "", export, flags=re.DOTALL)
    print(export)
    lines = export.split(",")
    lines = [line.strip() for line in lines if line.strip() != ""]
    print(lines)
    lines = [line.strip().split(":") for line in lines]
    enum_dict = { line[0]: line[1] for line in lines }
    return enum_dict

TS_BASE = "./@types/ol/"

fw = os.walk(TS_BASE)

# collect all generic classes for a second iteration 
# to add generic typing to extending classes 
generic_classes = []

while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if _file.endswith("d.ts"):
                ts_path = os.path.join(curr_dir_info[0], _file)
                # Open original js file (no .ts-file) for @typedefs
                js_path = ts_path.replace(".d.ts", ".ts")
                with open(js_path) as fh:
                    js_cont = fh.read()
                with open(ts_path) as fh:
                    cont = fh.read()
                print(ts_path)
                # generate a dictionnary with imports to 
                # path to resolve import paths
                import_dict = generate_import_dict(cont)
                js_import_dict = generate_import_dict(js_cont)
                print("IMPORT DICTS")
                print(js_import_dict)
                print(import_dict)
                print("IMPORT COUNT1: " + str(cont.count('import ')))
                cont = fix_imports(cont)
                print(cont)
                cont = mark_optional(cont)
                cont = no_never_returns(cont)
                cont = no_this_returns(cont)
                print("IMPORT COUNT2: " + str(cont.count('import ')))
                cont, generics = resolve_generics(cont)
                if len(generics):
                    generic_classes.extend(generics)
                # Some classes simply export an Object and tsc compiled 
                # to const, which can not serve as a type (e.g.: TextPlacement.js)
                # resolve by checking for jsdoc's @enum and rewrite as enum
                if "declare const _default: " in cont:
                    # parse the original js file for the original values 
                    # of the object, as tsc has mangled them to types
                    enum_dict = create_enum_dict(js_cont)
                    cont = replace_const_default_export(cont, enum_dict)
                print("IMPORT COUNT3: " + str(cont.count('import ')))
                # Problem: typedefs can be cut off during tsc-compilation
                # (-> see View.d.ts and View.js for an example)
                interfaces, interface_names, types, type_names, imports = \
                    typedef_to_interface(js_cont, import_dict, js_import_dict)
                print("RESULTING IMPORTS")
                print(imports)
                cont = add_after_import(cont, "\n".join(imports))
                if len(interfaces):
                    print("INTERFACES")
                    print(interfaces)
                    cont = add_after_import(cont, "\n".join(interfaces))
                    print("IMPORT COUNT3a: " + str(cont.count('import ')))
                if len(types):
                    print("TYPES")
                    print(types)
                    cont = add_after_import(cont, "\n".join(types))
                    print("IMPORT COUNT3b: " + str(cont.count('import ')))
                    print(types)
                print("IMPORT COUNT4: " + str(cont.count('import ')))
                has_own_object = len(interface_names) > 0
                cont = use_typed_options_in_constructor(cont, has_own_object, import_dict)
                cont = fix_duplicate_params(cont)
                with open(ts_path, "w+") as fh_out:
                    fh_out.write(cont)
    except StopIteration:
        break


## Second iteration to check if class extends a generic
fw = os.walk(TS_BASE)
# print("Adding generic typing to extending classes")
while True: 
    try:
        curr_dir_info = next(fw)
        for _file in curr_dir_info[2]:
            if _file.endswith("d.ts"):
                ts_path = os.path.join(curr_dir_info[0], _file)
                with open(ts_path) as fh:
                    cont = fh.read()
                rewrite = False
                extending_declarations = re.findall("declare class [a-zA-Z]* extends [a-zA-Z]* ", cont, re.MULTILINE)
                for declaration in extending_declarations:
                    decl_class = declaration.split(" ")[2]
                    base_class = declaration.split(" ")[4]
                    if base_class in generic_classes:
                        # print(declaration)
                        new_declaration = declaration.replace(base_class, base_class + "<T>")
                        new_declaration = new_declaration.replace(decl_class, decl_class + "<T>")
                        # print(new_declaration)
                        cont = cont.replace(declaration, new_declaration)
                        rewrite = True
                if rewrite:
                    with open(ts_path, "w+") as fh_out:
                        fh_out.write(cont)

    except StopIteration:
        break


## Apply some manual fixes 
# print("Applying manual fixes")
with open("manual-fixes.json") as fh:
    fixes = json.load(fh)
for fix in fixes:
    def_file = os.path.join(TS_BASE, fix["file"])
    # print(def_file)
    with open(def_file) as fh:
        cont = fh.read()
        cont = cont.replace(fix["original"], fix["replacement"])
    with open(def_file, "w+") as fh_out:
        fh_out.write(cont)
