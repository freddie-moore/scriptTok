# backend/api/routes.py
from flask import Blueprint, request, jsonify
from tasks import generate_script_task  # Import our Celery task

api = Blueprint('api', __name__)

@api.route('/generate-script', methods=['POST'])
def generate_script():
    """
    Starts the script generation task.
    Takes 'profile_name' and 'topic' from the request body.
    Returns a task ID immediately.
    """
    data = request.get_json()
    profile_name = data.get('profile_name')
    topic = data.get('topic')

    if not profile_name or not topic:
        return jsonify({'error': 'Missing profile_name or topic'}), 400

    # Start the background task using .delay()
    task = generate_script_task.delay(profile_name, topic)

    # Return the task ID to the client
    return jsonify({'task_id': task.id}), 202 # 202 Accepted

@api.route('/status/<task_id>', methods=['GET'])
def task_status(task_id):
    """
    Checks the status of a background task.
    The client polls this endpoint with the task ID.
    """
    task = generate_script_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state != 'FAILURE':
        response = {'state': task.state, 'status': 'Processing...'}
        if 'result' in task.info and task.info['result'] is not None:
             response['result'] = task.info['result']
    else:
        # Something went wrong in the background task
        response = {
            'state': task.state,
            'status': str(task.info),  # this is the exception raised
        }
    
    # If the task is successful, the result from the task is in task.result
    if task.state == 'SUCCESS':
         return jsonify({'state': task.state, 'result': task.result})

    return jsonify(response)