import requests
import pprint
import json
import sys
import os

DEV_DOCUMENTATION_DIRECTORY_PATH = 'docs/source/sections/progapi/progapi2_develop/'
JSON_FILE_DIRECTORY = 'endpoints_json_files'
JS_SPACE = '  '


try:
    resp = requests.get('https://api-dot-isb-cgc.appspot.com/_ah/api/discovery/v1/apis/cohort_api/v1/rest')
    # resp = requests.get('http://localhost:8080/_ah/api/discovery/v1/apis/cohort_api/v1/rest')
    RESP_JSON = resp.json()
except:
    with open(JSON_FILE_DIRECTORY + '/resp_json.json', 'r') as f:
        contents = f.read()
    RESP_JSON = json.loads(contents)


BASE_URL = RESP_JSON['baseUrl']


def get_index_of_nth_uppercase_char(a_string, n):
    '''
    Used to find the index of the nth uppercase letter in a string.
    Intended to find the third uppercase letter in a schema name,
    e.g. get_index_of_uppercase('ApiMetadataMetadataItem', 3) returns 11
    or None if there is no third uppercase letter
    '''
    count = 0
    i = 0
    # [letter for letter in a_string if letter.isupper()][n]
    for letter in a_string:
        if letter.isupper():
            count += 1
        if count == n:
            return i
        i += 1
    return None


def get_message_class_list():
    message_class_list = []
    for message_class in RESP_JSON['schemas'].keys():
        message_class_list.append(message_class)
    return sorted(message_class_list, key=lambda s: s[get_index_of_nth_uppercase_char(s, 3):].lower())


def get_methods_list():
    '''
    returns list of keys from methods object in RESP_JSON
    '''
    methods_list = []
    for method in RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'].keys():
        methods_list.append(method)
    return methods_list


def get_methods_pathnames_list():
    get_methods_pathnames_list = []
    for method in RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'].values():
        get_methods_pathnames_list.append(method['path'])
    return get_methods_pathnames_list


def get_csv_table_heading(headers=None, widths=None):
    # todo: change this so headers default is ["**Parameter name**", "**Value**", "**Description**"]
    # todo: make widths default [50, 10, 50]
    header_string = '.. csv-table::\n'
    if headers is None:
        header_string += '\t:header: "**Parameter name**", "**Value**", "**Description**"\n'
    if widths is None:
        header_string += '\t:widths: 50, 10, 50\n'
    return header_string


def get_next_parameter_javascript_row(message_class_name, started_string, level=0):
    '''
    Recursive function returning javascript formatting of restructured text.
    level will indicate number of JS_SPACE spaces
    todo: figure out tab spaces w nested objects vs lists of nested objects
    '''
    message_class_properties = RESP_JSON['schemas'][message_class_name]['properties']
    sorted_message_class_properties = list(sorted(message_class_properties.iteritems(),
                                                  key=lambda s: s[0].lower()))

    # print message_class_name + ": level " + str(level)
    for key, val in sorted_message_class_properties:
        # print key + ": level " + str(level)
        # possibilities
        # 1. value is a 'number' or 'string'
        if val.get('type') is not None and val.get('type') != 'array':
            started_string += (level+2)*JS_SPACE + '"{}": {}'.format(key, val.get('type'))
        # 2. value is a nested object message class
        if val.get('type') is None:
            started_string += (level+2)*JS_SPACE + '"' + key + '": {\n'
            next_message_class = val['$ref']
            level += 1
            started_string = get_next_parameter_javascript_row(next_message_class,
                                                               started_string,
                                                               level=level)
            level -= 1
        # 3. value is a list of either...
        if val.get('type') == 'array':
            # 3. a) i.e. this is a list of strings or numbers
            if val['items'].get('type') is not None:  # assuming no lists of lists so don't check for is not 'array'
                started_string += (level+2)*JS_SPACE + '"{}": [{}]'.format(key, val['items'].get('type'))
            # 3. b) value is a list of (nested?) object message classes
            else:
                started_string += (level+2)*JS_SPACE + '"{}": [\n'.format(key)
                level += 1
                started_string += + (level+2)*JS_SPACE + '{\n'
                next_message_class = val['items'].get('$ref')
                level += 1
                started_string = get_next_parameter_javascript_row(next_message_class,
                                                                   started_string,
                                                                   level=level)
                level -= 2
                started_string += '\n' + (level+2)*JS_SPACE + ']'
        # end possibilities

        # check if we are at the end of the message_class_properties
        current_index = sorted_message_class_properties.index((key, val))
        end_index = len(sorted_message_class_properties) - 1
        # if we are at the end
        if current_index == end_index:
            started_string += '\n'
            level -= 1
        # if we are not at the end, add a comma
        else:
            started_string += ",\n"

    started_string += (level+2)*JS_SPACE + '}'

    return started_string


def get_next_property_table_row(message_class_name, started_string, level=''):
    '''
    change name to get next response table row?
    Recursive function returning csv formatting of restructured text.
    level indicates number of dots
    '''
    message_class_properties = RESP_JSON['schemas'][message_class_name]['properties']
    sorted_message_class_properties = list(sorted(message_class_properties.iteritems(),
                                                  key=lambda s: s[0].lower()))

    description_filename = message_class_name[get_index_of_nth_uppercase_char(message_class_name,3):] + '.json'
    with open(JSON_FILE_DIRECTORY + '/' + description_filename, 'r+') as f:
        description_contents = f.read()
        description_json = json.loads(description_contents)

    for key, val in sorted_message_class_properties:
        # possibilities
        # 1. value is a number or string
        if val.get('type') is not None and val.get('type') != 'array':
            started_string += '\t{level}{key}, {type}, "{desc}"\n'\
                .format(level=level,
                        key=key,
                        type=val.get('type'),
                        desc=description_json[key])

        # 2. value is a nested object message class
        if val.get('type') is None:
            started_string += '\t{level}{key}, nested object, "{desc}"\n'\
                .format(level=level, key=key, desc=description_json[key])
            level += key + '.'  # will this work?
            next_message_class = val['$ref']
            started_string = get_next_property_table_row(next_message_class,
                                                         started_string,
                                                         level=level)
            # go up one level i.e. truncate at next to last dot
            level = level[:level[:level.rfind('.')].rfind('.')+1]
        # 3. value is a list of either...
        if val.get('type') == 'array':
            started_string += '\t{level}{key}[], list, "{desc}"\n'\
                .format(level=level, key=key, desc=description_json[key])
            # 3. a) i.e. this is a list of strings or numbers
            if val['items'].get('type') is not None:  # assuming no lists of lists so don't check for is not 'array'
                pass
            # 3. b) value is a list of nested object message classes
            else:
                level += key + '[].'
                next_message_class = val['items'].get('$ref')
                started_string = get_next_property_table_row(next_message_class,
                                                             started_string,
                                                             level=level)
                # go up one level i.e. truncate at next to last dot
                level = level[:level[:level.rfind('.')].rfind('.')+1]

    return started_string

def create_new_rst_file(method_name):
    '''
    creates an rst file with the name of the endpoint method
    in the folder docs/sections/progapi/progapi2
    '''
    file_name = method_name + ".rst"
    file_path = str(DEV_DOCUMENTATION_DIRECTORY_PATH + file_name)
    f = open(file_path, 'w')
    f.close()


def write_rst_file_header(method):
    '''
    write the title heading,
     description
     access control
     request (GET or POST) and the full url
     example of usage?
    '''
    method_json = RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'][method]
    method_path_name = method_json['path']  # todo: put backslash in front of underscores?
    description = method_json['description']
    http_method = method_json['httpMethod']
    file_name = method_path_name + '.rst'

    example = '\n\n'

    header_text = "{method_path_name}\n{underscore}\n".format(
        method_path_name=method_path_name,
        underscore='#'*len(method_path_name))
    header_text += "{description}{example}\n\nRequest\n\nHTTP request\n\n".format(
        description=description, example=example)
    header_text += "{http_method} {base_url}{method_path_name}``\n\n".format(
        method_path_name=method_path_name,
        http_method=http_method,
        base_url=BASE_URL)

    with open(DEV_DOCUMENTATION_DIRECTORY_PATH + file_name, 'w+') as f:
        f.write(header_text)


def get_next_parameter_table_row(parameter_json, method_name=None):
    '''
    No need for this to be a recursive function since request parameters
    are only a list. Takes a json object of parameters and returns a string
    for a csv-formatted rst table.
    '''
    sorted_parameter_json = list(sorted(parameter_json.iteritems(), key=lambda s: s[0].lower()))
    return_string = ''
    for key, val in sorted_parameter_json:
        # todo: zip descriptions with key name, maybe just for preview and save cohort?
        description = "Required." if val.get('required') else 'Optional.'
        value_entry = 'list' if val.get('type') == 'array' else val.get('type')
        # todo: if val['type'] is "string" but val['format'] is "int64", label as such??
        return_string += '\t{}{},{},{}\n'.format(key,
                                                 '[]' if value_entry == 'list' else '',
                                                 value_entry,
                                                 description)

    return return_string


def write_rst_file_path_parameters(method):
    '''
    rst table from csv table of path parameters
    '''
    method_json = RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'][method]
    method_path_name = method_json['path']
    file_name = method_path_name + '.rst'
    method_parameters = method_json.get('parameters')
    if method_parameters is None:
        parameter_text = """Parameters\n\nNone\n\n"""
    else:
        csv_table_heading = get_csv_table_heading()
        csv_table_body = get_next_parameter_table_row(method_parameters)

        parameter_text = """Parameters\n\n{csv_header}\n{csv_table_body}\n\n"""\
            .format(csv_header=csv_table_heading,
                   csv_table_body=csv_table_body)


    # todo: f.read(), then f.seek() to find "Parameters" and replace text
    # from just the parameters section
    with open(DEV_DOCUMENTATION_DIRECTORY_PATH + file_name, 'a+') as f:
        f.write(parameter_text)


def write_rst_file_request_body(method):
    '''
    write javascript code block of request body parameters
    and rst table from csv table of request body parameters
    '''
    method_json = RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'][method]
    method_path_name = method_json['path']
    file_name = method_path_name + '.rst'
    method_request = method_json.get('request')
    if method_request is None:
        return
    request_body_message_class_name = method_request['$ref']  # e.g. "ApiMetadataIncomingMetadataItem"

    request_desc = 'In the request body, supply a metadata resource:'
    js_block_header = '.. code-block:: javascript\n\n'
    message_class_properties = RESP_JSON['schemas'][request_body_message_class_name]['properties']
    js_block_body = get_next_parameter_javascript_row(request_body_message_class_name,
                                                      JS_SPACE + '{\n')
    csv_header = get_csv_table_heading()
    csv_body = get_next_parameter_table_row(message_class_properties)

    request_body_text = "Request body\n\n{}\n\n{}{}\n\n{}\n{}\n\n"\
        .format(request_desc, js_block_header, js_block_body, csv_header, csv_body)
    with open(DEV_DOCUMENTATION_DIRECTORY_PATH + file_name, 'a+') as f:
        f.write(request_body_text)


def write_rst_file_response_section(method):
    '''
    write javascript code block of response body properties
    and rst table from csv table of response body properties
    '''
    method_json = RESP_JSON['resources']['cohort_endpoints']['resources']['cohorts']['methods'][method]
    method_path_name = method_json['path']
    file_name = method_path_name + '.rst'

    method_response = method_json.get('response')
    if method_response is None:
        response_body_text = 'Response\n\nNone'
    else:
        response_desc = 'If successful, this method returns a response body with the following structure:\n\n'
        js_block_header = '.. code-block:: javascript\n\n'
        response_body_message_class_name = method_response.get('$ref')
        js_block_body = get_next_parameter_javascript_row(response_body_message_class_name,
                                                          JS_SPACE + '{\n')
        csv_header = get_csv_table_heading()
        csv_body = get_next_property_table_row(response_body_message_class_name, '')
        response_body_text = 'Response\n\n{}{}{}\n\n{}\n{}'.format(
            response_desc, js_block_header, js_block_body, csv_header, csv_body)

    with open(DEV_DOCUMENTATION_DIRECTORY_PATH + file_name, 'a+') as f:
        f.write(response_body_text)


def main():

    # methods_list = get_methods_list()
    # methods_pathnames_list = get_methods_pathnames_list()
    # for method_path_name in methods_pathnames_list:
    #     create_new_rst_file(method_path_name)

    methods_list = ['sample_details']

    for method in methods_list:
        write_rst_file_header(method)
        write_rst_file_path_parameters(method)
        write_rst_file_request_body(method)
        write_rst_file_response_section(method)


if __name__ == '__main__':
    main()
