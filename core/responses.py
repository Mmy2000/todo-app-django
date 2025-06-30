from rest_framework.response import Response


class CustomResponse(Response):
    def __init__(self, data=None, status=None, message=None, template_name=None, headers=None, exception=False,
                 content_type=None, pagination=None):
        non_field_keys = ['non_field_errors', 'detail', 'details']

        if status and status < 400:
            message = message if message else 'Success'
        else:
            if not message:
                if isinstance(data, dict):
                    # Handle dictionary error response
                    for key in data:
                        if key in non_field_keys:
                            message = data[key]
                            if isinstance(message, list):
                                message = message[0]
                            break
                    else:
                        # Default handling if no non-field key is found
                        error_key = next(iter(data))
                        error_message = data[error_key]
                        if isinstance(error_message, list):
                            message = error_message[0]
                        elif isinstance(error_message, str):
                            message = error_message
                        else:
                            message = str(error_message)
                elif isinstance(data, list):
                    # Handle list error response
                    error_message = data[0]
                    if isinstance(error_message, dict):
                        # Extract first error from the dict
                        for key in error_message:
                            if key in non_field_keys:
                                message = error_message[key]
                                if isinstance(message, list):
                                    message = message[0]
                                break
                        else:
                            # Default handling if no non-field key is found
                            error_key = next(iter(error_message))
                            message = error_message[error_key]
                            if isinstance(message, list):
                                message = message[0]
                            elif not isinstance(message, str):
                                message = str(message)
                    elif isinstance(error_message, str):
                        message = error_message
                    else:
                        message = str(error_message)
                else:
                    # Handle other types of error response (e.g., string)
                    message = str(data)
                data = {}

        custom_data = {
            'status_code': int(status),
            'data': data,
            'message': message,
            'pagination': pagination,
        }
        super().__init__(custom_data, status, template_name, headers, exception, content_type)
