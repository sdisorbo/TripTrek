from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from openai import OpenAI
import os
import requests
import json
import datetime

app = Flask(__name__)
app.secret_key = 'sam'  # Set a secure secret key for session management


# Initialize the OpenAI client

client = OpenAI(
  api_key="key")
YELP_API_KEY = 'key'

date = datetime.datetime.now()

# The travel API function as provided
def travel_api(departDate, toEntityId, fromEntityId, adults=1, children=0, infants=0):
    url = "https://sky-scanner3.p.rapidapi.com/flights/search-multi-city"
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "sky-scanner3.p.rapidapi.com",
        "x-rapidapi-key": "key"  # Make sure to use a valid API key
        }

    #if adults is NA, make it into 1
    if adults == "NA":
        adults = 1
    #if children is NA, make it into 0
    if children == "NA":
        children = 0
    #if infants is NA, make it into 0
    if infants == "NA":
        infants = 0

    # Define the data payload
    data = {
        "market": "US",
        "locale": "en-US",
        "currency": "USD",
        "adults":  adults,
        "children": children,
        "infants": infants,
      #  "cabinClass": "economy",
        "flights": [
            {
                "fromEntityId": fromEntityId,  # Ensure this is the correct code for your departure airport
                "toEntityId": toEntityId,     # Ensure this is the correct code for your arrival airport
                "departDate": departDate
            }
        ],
        #"stops": ["direct", "1stop", "2stops"],  # Consider removing this to see if it affects results
        "sort": "cheapest_first",
        #"airlines": [-32753, -32695]  # Ensure these IDs are correct for your desired airlines
    }

    # Make the POST request
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # Check the response
    if response.status_code == 200:
        result = response.json()
        #only take the first three results if there are more
        if len(result["data"]["itineraries"]) > 3:
            result = result["data"]["itineraries"][:3]
        else:
            result = result["data"]["itineraries"]
    else:
        print("Error:", response.status_code, response.text)

    return result



def search_hotels(location, check_in_date, check_out_date, adults):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_hotels",  # API engine
        "q": location, #  # (e.g., "Ann Arbor, MI")
        "check_in_date": check_in_date,  # Format: YYYY-MM-DD
        "check_out_date": check_out_date,  # Format: YYYY-MM-DD
        "adults": adults,  # Number of adults
        "currency": "USD",  # Currency for prices
        "api_key": "key"

    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        #return top 3 hotels if available
        result = response.json()
        #remove images, serpapi_property_details_link fields from the response
        if "properties" in result and result["properties"]:
            for property in result["properties"]:
                property.pop("images", None)
                property.pop("serpapi_property_details_link", None)
        if len(result["properties"]) > 3:
            result = result["properties"][:3]
        else:
            result = result["properties"]
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    return result
    
def search_restaurants(payload):
    # Yelp API endpoint and headers
    YELP_URL = 'https://api.yelp.com/v3/businesses/natural_language_search'
    YELP_HEADERS = {
        'Authorization': f'Bearer {YELP_API_KEY}',
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    # Set up the headers for authorization and content type
    headers = YELP_HEADERS
    # Make the request (POST method)
    response = requests.post(YELP_URL, headers=headers, data=json.dumps(payload))
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        # Print or process the data as needed
        return data
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        print(response.text)

def add_to_cart(messages, request_load):
    gpt_prompt = f"""
    Act as a travel assistant that when the user asks to add something to the cart, you will extrct the text that they are referring to and return it, formatting as an itinerary item. 
    Here is the message history of options you have provided to them. 
    {messages}
    Here is their request to add something to the cart:
    {request_load}
    Please extract the text that they are referring to and return it, presenting it as an itinerary item. For a flight do like, the flight number, airline price and time and cost and to and from. For
    a hotel, do the hotel name, price, and location. For a restaurant, do the restaurant name, price, and location Be sure to specify times/dates for the flights and hotels.
    """
    
     # Call GPT API to process the conversation
    completion = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=gpt_prompt, max_tokens=200)

    gpt_response = completion.choices[0].text
   
   
    # Step 5: Return the final GPT-generated summary
    return gpt_response

        
# Evaluate trip options function
def evaluate_trip_options(options):
    """
    Function assistant agent to evaluate trip options based on user flight API response. Will receive a list of JSON objects from the response from the API. This
    This function should look throught them and summarize the options from the response.
    It should return a list of the options ordered by number.
    It should say (Recommended Option) for the best one to fit the criteria.
    """
    
   
    gpt_prompt = f"""
    Act as an assistant agent to show the user the flight options returned. 
    look through the response options and summarize the options from the response.
    It should return a list of the options ordered by number.
    It should say (Recommended Option) for the best one to fit the criteria.
    In every option outline, give the url to the booking site (the airline website) and the flight number, as well as the flight price, flight time, and other relevant information.
    List the options like:
    Option 1, info...
    Option 2, info...
    Option 3 (Recommended), info...
    etc.
    IMPORTANT: Include line breaks between each option and make it easy to read. ONCE ONE OPTION ENDS, END THE LINE AND START THE NEXT OPTION ON THE NEXT LINE.
    Don't format it in JSON format at all, make it all natural language and easy to read.
    Don't include tags or overall scores in the response
    Here are the options returned by the API:
    {options}
    Here is today's date:
    {date}
    """
    
     # Call GPT API to process the conversation
    completion = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=gpt_prompt, max_tokens=400)

    gpt_response = completion.choices[0].text
   
   
    # Step 5: Return the final GPT-generated summary
    return gpt_response

def evaluate_trip_options_hotel(options):
    """
    Function assistant agent to evaluate trip options based on user hotel API response. Will receive a list of JSON objects from the response from the API. This
    This function should look throught them and summarize the options from the response.
    It should return a list of the options ordered by number.
    It should say (Recommended Option) for the best one to fit the criteria.
    """
    
   
    gpt_prompt = f"""
    Act as an assistant agent to show the user the hotel options returned. 
    look through the response options and summarize the options from the response.
    It should return a list of the options ordered by number.
    It should say (Recommended Option) for the best one to fit the criteria.
    In every option outline, give the hotel name price and average rating
    List the options like:
    Option 1, info...
    Option 2, info...
    Option 3 (Recommended), info...
    etc.
    IMPORTANT: Include line breaks between each option and make it easy to read. ONCE ONE OPTION ENDS, END THE LINE AND START THE NEXT OPTION ON THE NEXT LINE.
    DON'T format it in JSON format at all, make it all natural language and easy to read.
    Don't include tags or overall scores in the response
    Here are the options returned by the API:
    {options}
    Here is today's date:
    {date}
    """
    
     # Call GPT API to process the conversation
    completion = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=gpt_prompt, max_tokens=400)

    gpt_response = completion.choices[0].text
   
   
    # Step 5: Return the final GPT-generated summary
    return gpt_response

def eval_api_res(options):
    """
    Function assistant agent to evaluate restaurant options based on an API response. Will receive a list of JSON objects from the response from the API. This
    This function should look throught them and summarize the options from the response.
    It should return a list of the options ordered by number.
    It should say (Recommended Option) for the best one to fit the criteria.
    """
    
   
    gpt_prompt = f"""
    Act as an assistant agent to evaluate restaurant options based on an API response. 
    List the options, separated by name, and provide a summary of what they offer
    Include for the options things like the name, location, price, rating, and any other relevant information (vibe, reviews, etc.)
    Don't format it in JSON format at all, make it all natural language and easy to read.
    Give the output in the form of a list of options, with each option numbered and a summary of the information provided:
    Restaurant 1 Name: info...with new lines between each option and fact.
    Here are the options returned by the API:
    {options}
    """
    
     # Call GPT API to process the conversation
    completion = client.completions.create(model="gpt-3.5-turbo-instruct", prompt=gpt_prompt, max_tokens=250)

    gpt_response = completion.choices[0].text
    
   
    # Step 5: Return the final GPT-generated summary
    return gpt_response


parameters = [
    {   "name": "search_flights",
        "description": "Search for flights based on user input",
        "parameters": {
            "type": "object",
            "properties": {
                        "departDate": {"type": "string", "description": "date of departure"},
                        "toEntityId": {"type": "string", "description": "Location of the airport you want to fly to"},
                        "fromEntityId": {"type": "string", "description": "Location of the airport you want to fly from"},
                    # "cabinClass": {"type": "number", "description": "Cabin class"},
                        "adults": {"type": "number", "description": "Number of adults"},
                        "children": {"type": "boolean", "description": "Number of children"},
                        "infants": {"type": "string", "description": "Number of infants"}
            },
            "required": ["departDate", "toEntityId", "fromEntityId"]
        }
    },
    {
        "name": "search_hotels",
        "description": "Search for hotels based on user input",
        "parameters": {
            "type": "object",
            "properties": {
                        "location": {"type": "string", "description": "Location of the hotel"},
                        "check_in_date": {"type": "string", "description": "Check-in date"},
                        "check_out_date": {"type": "string", "description": "Check-out date"},
                        "adults": {"type": "number", "description": "Number of adults"},
                        "currency": {"type": "string", "description": "Currency for prices"}
            },
            "required": ["location", "check_in_date", "check_out_date", "adults"]
        }
    },
    {
        "name": "search_restaurants",
        "description": "Search for restaurants based on user input",
        "parameters": {
            "type": "object",
            "properties": {
                    "location": {"type": "string", "description": "Location of the restaurant"},
                    "cuisine": {"type": "string", "description": "Type of cuisine"},
                    "price": {"type": "string", "description": "Price range"},
                    "rating": {"type": "number", "description": "Minimum rating"},
                    "distance": {"type": "number", "description": "Maximum distance"},
                    "open_now": {"type": "boolean", "description": "Whether the restaurant is open now"},
                    "vibe": {"type": "string", "description": "Type of vibe"},
                    "dietary_restrictions": {"type": "array", "items": {"type": "string"}, "description": "Dietary restrictions"},
                    "popularity": {"type": "string", "description": "Popularity level"}
        },
            "required": ["location", "cuisine"],
        }
    }
]

tools = [
    {
         "type": "function",
        "function": {
            'name': 'search_flights', 
            'description': 'Search for restaurants based on user input', 
            'parameters': {
                "type": "object",
                "properties": {
                    "departDate": {"type": "string", "description": "date of departure"},
                    "toEntityId": {"type": "string", "description": "Location of the airport you want to fly to"},
                    "fromEntityId": {"type": "string", "description": "Location of the airport you want to fly from"},
                    #"cabinClass": {"type": "number", "description": "Cabin class"},
                    "adults": {"type": "number", "description": "Number of adults"},
                    "children": {"type": "boolean", "description": "Number of children"},
                    "infants": {"type": "string", "description": "Number of infants"}
                },
            "required": ["departDate", "toEntityId", "fromEntityId"]
             }
            }
    },
    {
        "type": "function",
        "function": {
        "name": "search_hotels",
        "description": "Search for hotels based on user input",
        "parameters": {
            "type": "object",
            "properties": {
                        "location": {"type": "string", "description": "Location of the hotel"},
                        "check_in_date": {"type": "string", "description": "Check-in date"},
                        "check_out_date": {"type": "string", "description": "Check-out date"},
                        "adults": {"type": "number", "description": "Number of adults"},
                        "currency": {"type": "string", "description": "Currency for prices"}
            },
            "required": ["location", "check_in_date", "check_out_date", "adults"]
         }
        }
    },
    {
         "type": "function",
        "function": {
            'name': 'search_restaurants', 
            'description': 'Search for restaurants based on user input', 
            'parameters': {
                "type": "object",
                "properties": {
                            "location": {"type": "string", "description": "Location of the restaurant"},
                            "cuisine": {"type": "string", "description": "Type of cuisine"},
                            "price": {"type": "string", "description": "Price range"},
                            "rating": {"type": "number", "description": "Minimum rating"},
                            "distance": {"type": "number", "description": "Maximum distance"},
                            "open_now": {"type": "boolean", "description": "Whether the restaurant is open now"},
                            "vibe": {"type": "string", "description": "Type of vibe"},
                            "dietary_restrictions": {"type": "array", "items": {"type": "string"}, "description": "Dietary restrictions"},
                            "popularity": {"type": "string", "description": "Popularity level"}
                },
                "required": ["location", "cuisine"],
             }
            }
    }
]

messages = []
messages.append({"role": "system", "content": "You are a helpful travel agent. Use the supplied tools to assist the user. Do not try to plan the entire trip, or anything outside of their flight or hotel or food desires."})
payload = {"messages": []}

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)  # Remove the cart from the session
    return jsonify({"response": "Cart cleared."})


@app.route('/shopping_cart', methods=['GET'])
def shopping_cart():
   # Check if the page was refreshed
    if session.get('refreshed', False):
        # Do not clear the cart unless explicitly intended
        session['refreshed'] = False  # Reset the refresh tracker
    else:
        # Set refreshed tracker for the first page load
        session['refreshed'] = True

    # Ensure session persists for the current session
    session.permanent = True

    # Retrieve the cart items from the session (or default to an empty list)
    cart_items = session.get('cart', [])

    # Return the cart items to the template
    return render_template('shopping_cart.html', cart_items=cart_items)


@app.route('/', methods=['POST'])
def chat():
    user_input = request.json.get("user_input")
    messages.append({"role": "user", "content": user_input})
    #if the string contains 'food' drink' or 'restaurant' call the search_restaurants function add the string to the payload
    if 'food' in user_input or 'drink' in user_input or 'restaurant' in user_input:
        payload["messages"].append({"role": "user", "content": user_input})

    #if add to cart is in the string, call the add_to_cart function
    if 'add to itinerary' in user_input.lower() or 'to my itinerary' in user_input.lower():
        gpt_response = add_to_cart(messages, user_input)
        
        # Initialize cart in session if it doesn't exist
        if 'cart' not in session:
            session['cart'] = []
        
        # Append the new item to the cart
        session['cart'].append(gpt_response)
        session.modified = True  # Mark session as modified
        return jsonify({"response": "Item added to itinerary."})
       
    
    # Get the GPT response based on the input message
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        tools=tools,
    )

    finish_reason = response.choices[0].finish_reason
    assistant_response = ""

    if finish_reason == 'stop':
        assistant_response = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_response})
        
    elif finish_reason == 'tool_calls':
        tool_call = response.choices[0].message.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        print(arguments)


        if tool_call.function.name == "search_flights":
            # Call travel API

            arguments.setdefault("adults", 1)
            arguments.setdefault("children", 0)
            arguments.setdefault("infants", 0)

            result = travel_api(
                departDate=arguments["departDate"],
                toEntityId=arguments["toEntityId"],
                fromEntityId=arguments["fromEntityId"],
                adults=arguments["adults"],
                children=arguments["children"],
                infants=arguments["infants"]
            )
            # Evaluate options
            assistant_response = evaluate_trip_options(result)
            messages.append({"role": "assistant", "content": assistant_response})
        elif tool_call.function.name == "search_hotels":
            # Call hotel search API
            result = search_hotels(
                location=arguments["location"],
                check_in_date=arguments["check_in_date"],
                check_out_date=arguments["check_out_date"],
                adults=arguments["adults"],
            )
            print(result)
            assistant_response = evaluate_trip_options_hotel(result)
            messages.append({"role": "assistant", "content": assistant_response})
        elif tool_call.function.name == "search_restaurants":
            tool_call = response.choices[0].message.tool_calls[0]
            arguments = json.loads(tool_call.function.arguments)


            # Call the function with the extracted arguments and print the result
            result = search_restaurants(
                payload = payload
            )
            gpt = eval_api_res(result)
            assistant_response = gpt
            # Evaluate options
            messages.append({"role": "assistant", "content": gpt})

    else:
        assistant_response = "I didn't understand that. Can you provide more details?"

    return jsonify({"response": assistant_response})



@app.route('/')
def index():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
