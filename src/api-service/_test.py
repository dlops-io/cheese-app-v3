# import os
# import glob
# import json

# # Tensorflow
# import numpy as np
# import tensorflow as tf
# from tensorflow import keras

# print("Testing...")
# print("tensorflow version", tf.__version__)
# print("Eager Execution Enabled:", tf.executing_eagerly())

# local_experiments_path = "/persistent/experiments"
# experiment_name = "experiment_1760994796"
# best_model = os.path.join(
#     local_experiments_path, experiment_name, "mobilenetv2_train_base_True.keras"
# )
# print(best_model)

# # Load a model from disk
# prediction_model = tf.keras.models.load_model(best_model)
# print(prediction_model.summary())

# image_width = 224
# image_height = 224
# num_channels = 3


# # Prepare the data
# def preprocess_image(path):
#     image = tf.io.read_file(path)
#     image = tf.image.decode_jpeg(image, channels=num_channels)
#     image = tf.image.resize(image, [image_height, image_width])

#     image = keras.applications.mobilenet.preprocess_input(image)

#     return image


# data_details_path = os.path.join(
#     local_experiments_path, experiment_name, "data_details.json"
# )

# # Load data details
# with open(data_details_path, "r") as json_file:
#     data_details = json.load(json_file)

# sample_images_path = "/persistent/cheeses_unlabeled"
# prediction_image_paths = glob.glob(os.path.join(sample_images_path, "*.jpg"))
# prediction_image_paths = prediction_image_paths[:5]
# # Prepare the data for prediction
# prediction_data = tf.data.Dataset.from_tensor_slices((prediction_image_paths))
# prediction_data = prediction_data.map(
#     preprocess_image, num_parallel_calls=tf.data.AUTOTUNE
# )
# prediction_data = prediction_data.batch(len(prediction_image_paths))

# # Make prediction
# predictions = prediction_model.predict(prediction_data)
# print("predictions.shape:", predictions.shape)
# print("Example prediction output:")
# print(predictions[0], predictions[0].argmax())

# # Prediction Labels
# for prediction in predictions:
#     prediction_label = data_details["index2label"][str(prediction.argmax())]
#     print("Prediction Label:", prediction_label)


"""
Simple Chat Examples using Google Generative AI Python SDK

This script demonstrates:
1. Starting a new chat conversation
2. Continuing a conversation with history
"""
import os
from google import genai
from google.genai import types
import traceback

GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 256
GENERATIVE_MODEL = "gemini-2.0-flash"
#############################################################################
#                       Initialize the LLM Client                           #
llm_client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)
#############################################################################

# ============================================================================
# EXAMPLE 1: Starting a New Chat
# ============================================================================


def example_new_chat():
    """Start a fresh chat conversation"""
    print("=" * 60)
    print("EXAMPLE 1: Starting a New Chat")
    print("=" * 60)

    # Create a new chat session
    chat = llm_client.chats.create(model=GENERATIVE_MODEL)
    print(chat)
    print(type(chat))

    # Send the first message
    print("\nUser: Tell me a short story about a robot")
    response = chat.send_message("Tell me a short story about a robot")
    print(f"\nAssistant: {response.text}")

    # Continue the conversation - the chat remembers context
    print("\n" + "-" * 60)
    print("\nUser: What was the robot's name?")
    response = chat.send_message("What was the robot's name?")
    print(f"\nAssistant: {response.text}")

    # Another follow-up - still in the same conversation
    print("\n" + "-" * 60)
    print("\nUser: Summarize the story in one sentence")
    response = chat.send_message("Summarize the story in one sentence")
    print(f"\nAssistant: {response.text}")
    print()


# ============================================================================
# EXAMPLE 2: Continuing a Conversation with Past History
# ============================================================================


def example_continue_with_history_xxx():
    """Continue a conversation using explicit history"""
    print("=" * 60)
    print("EXAMPLE 2: Continuing with Past History")
    print("=" * 60)

    # Define past conversation history
    # This simulates a conversation that happened before
    past_history = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="Hello! My name is Alice and I love astronomy."
                )
            ],
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text="Hello Alice! It's wonderful to meet someone interested in astronomy. "
                    "What aspects of astronomy fascinate you the most?"
                )
            ],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="I am particularly interested in black holes."
                )
            ],
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text="Black holes are fascinating! They're some of the most extreme objects in the universe. "
                    "Is there something specific about black holes you'd like to know more about?"
                )
            ],
        ),
    ]

    # Create a new chat with the model
    chat = llm_client.chats.create(model=GENERATIVE_MODEL)

    # To "continue" the conversation, we need to send the history as context
    # We do this by including the history in our next generate_content call
    # Note: The chats.create() doesn't take history directly, so we'll use
    # generate_content with the full conversation context

    print("\n[Previous conversation context loaded...]")
    print("\nPast conversation:")
    for content in past_history:
        role = "User" if content.role == "user" else "Assistant"
        print(f"{role}: {content.parts[0].text}")

    # Now continue the conversation with a new message
    print("\n" + "-" * 60)
    print("\nUser: Can you remind me what we were discussing?")

    # Add the new user message to the history
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Can you remind me what we were discussing?")],
    )

    # Generate response with full context (history + new message)
    response = llm_client.models.generate_content(
        model=GENERATIVE_MODEL, contents=past_history + [new_message]
    )

    print(f"\nAssistant: {response.text}")

    # Continue further with updated history
    print("\n" + "-" * 60)
    print("\nUser: Tell me about Hawking radiation")

    # Update history with previous response and new message
    past_history.append(new_message)
    past_history.append(
        types.Content(role="model", parts=[types.Part.from_text(text=response.text)])
    )

    new_message2 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Tell me about Hawking radiation")],
    )

    response = llm_client.models.generate_content(
        model=GENERATIVE_MODEL, contents=past_history + [new_message2]
    )

    print(f"\nAssistant: {response.text}")
    print()


def example_continue_with_history():
    """Continue a conversation using explicit history"""
    print("=" * 60)
    print("EXAMPLE 2: Continuing with Past History")
    print("=" * 60)

    # Define past conversation history
    # This simulates a conversation that happened before
    # Note: Use UserContent for user messages and ModelContent for assistant messages
    past_history = [
        types.UserContent(
            parts=[
                types.Part.from_text(
                    text="Hello! My name is Alice and I love astronomy."
                )
            ]
        ),
        types.ModelContent(
            parts=[
                types.Part.from_text(
                    text="Hello Alice! It's wonderful to meet someone interested in astronomy. "
                    "What aspects of astronomy fascinate you the most?"
                )
            ]
        ),
        types.UserContent(
            parts=[
                types.Part.from_text(
                    text="I am particularly interested in black holes."
                )
            ]
        ),
        types.ModelContent(
            parts=[
                types.Part.from_text(
                    text="Black holes are fascinating! They're some of the most extreme objects in the universe. "
                    "Is there something specific about black holes you'd like to know more about?"
                )
            ]
        ),
    ]

    print("\n[Previous conversation context loaded...]")
    print("\nPast conversation:")
    for content in past_history:
        role = "User" if content.role == "user" else "Assistant"
        print(f"{role}: {content.parts[0].text}")

    # Create a chat session WITH the history parameter
    # This is the correct way to continue from past conversation!
    chat = llm_client.chats.create(model="gemini-2.5-flash", history=past_history)

    # Now continue the conversation - the chat already has the context
    print("\n" + "-" * 60)
    print("\nUser: Can you remind me what we were discussing?")

    response = chat.send_message("Can you remind me what we were discussing?")
    print(f"\nAssistant: {response.text}")

    # Continue further - the chat maintains all history including what we just added
    print("\n" + "-" * 60)
    print("\nUser: Tell me about Hawking radiation")

    response = chat.send_message("Tell me about Hawking radiation")
    print(f"\nAssistant: {response.text}")
    print(type(response))
    print(type(response.text))

    # You can also inspect the full conversation history
    # print(f"\n[Total messages in chat history: {len(chat._history)}]")
    print()


# ============================================================================
# BONUS: Alternative approach using generate_content for session management
# ============================================================================


def example_manual_history_management():
    """Manage conversation history manually for full control"""
    print("=" * 60)
    print("BONUS: Manual History Management")
    print("=" * 60)

    # Initialize empty history
    conversation_history = []

    def chat_with_history(user_message):
        """Helper function to chat while maintaining history"""
        # Add user message to history
        conversation_history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )

        # Generate response with full history
        response = llm_client.models.generate_content(
            model=GENERATIVE_MODEL, contents=conversation_history
        )

        # Add model response to history
        conversation_history.append(
            types.Content(
                role="model", parts=[types.Part.from_text(text=response.text)]
            )
        )

        return response.text

    # Use the helper function
    print("\nUser: What's the capital of France?")
    response = chat_with_history("What's the capital of France?")
    print(f"Assistant: {response}")

    print("\n" + "-" * 60)
    print("\nUser: What's its population?")
    response = chat_with_history("What's its population?")
    print(f"Assistant: {response}")

    print("\n" + "-" * 60)
    print("\nUser: What was my first question?")
    response = chat_with_history("What was my first question?")
    print(f"Assistant: {response}")

    print(f"\n[Total messages in history: {len(conversation_history)}]")
    print()


# ============================================================================
# Run the examples
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🤖 GOOGLE GENERATIVE AI - CHAT EXAMPLES 🤖".center(60))
    print()

    try:
        # Run Example 1: New chat
        # example_new_chat()

        # Run Example 2: Continue with history
        example_continue_with_history()

        # Run Bonus: Manual history management
        # example_manual_history_management()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
