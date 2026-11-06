from llm_provider import LLM
from bs4 import BeautifulSoup
from website_provider import getValue
from headless_browser import HeadlessBrowser

from pydantic import BaseModel
class UserQueryJson(BaseModel):
    item_name: str
    search_query: str
    constraints: str
    preference: str
    specs_to_check: list['str']

def parse_user_query(user_query, user_info_xml):
    soup = BeautifulSoup(user_info_xml, features='xml')
    req = {'user_info': user_info_xml}
    sys_prompt_for_query = '''
You are an online shopping assistant. You are given the user personality and the user's request.
You're in India, so Indian rupees is the currency for any price specification.

Summarize this information into a JSON object with the following 4 fields.
1. item_name: name of the item required (like 'laptop')
2. search_query: what should the user type in the search bar (eg 'laptops under 70000')
3. constraints: a list of all the constraints (budget, delivery speed, etc.) mentioned by the user
4. preference: what the user prefers in context of the product
5. specs_to_check: a list of the main specifications to check for while buying the item
    '''
    user_prompt_for_query = f'''
<PERSONALITY>{soup.find('personality')}</PERSONALITY>
<REQUIREMENT>{user_query}</REQUIREMENT>
    '''
    res = LLM.generate(system_prompt=sys_prompt_for_query, user_prompt=user_prompt_for_query, format=UserQueryJson.model_json_schema())
    info = UserQueryJson.model_validate_json(res)
    req = req | info.__dict__
    req['avg_cost'] = getValue(LLM.websearch(f'How much does a {req['item_name']} normally cost in rupees? Output ONLY the number.').replace('X','0'))
    req['original_query'] = user_query
    return req

def llm_rate(requirements, product):
        system_prompt_for_rating = f'''
The user wants to buy a {requirements['item_name']}.

Check if the product satisfies the required constraints. If it doesn't satisfy the constraints, output -1.
OTHERWISE rate it out of 100 with: 0 being 'very bad', 50 being 'average', 100 being 'very good'.
Your output MUST BE A NUMBER BETWEEN -1 AND 100 and NOTHING ELSE. (No reasoning)
        '''
        user_prompt_for_rating = f'''
<CONSTRAINTS>{requirements['constraints']}</CONSTRAINTS>
Here is the description of {product['name']}.
<PRICE>{product['price']}</PRICE>
<DISCOUNT>{product['discount']}</DISCOUNT>
<TOP FEATURES>{product['features']}</TOP FEATURES>
<SPECIFICATIONS>
{product['top_specs']}
</SPECIFICATIONS>
        '''
        res = LLM.generate(system_prompt=system_prompt_for_rating, user_prompt=user_prompt_for_rating)
        rating = 0
        try:
            rating = float(res)
            assert 100 >= rating >= -1
        except:
            print(f"INVALID RATING: {res}")
        return rating

def find_options(requirements, providers):
    search_query = requirements['search_query']
    options = []
    HeadlessBrowser.init_browser()
    for p in providers:
        options += p.search(search_query)
    HeadlessBrowser.quit()
    for option in options:
        option['llm_rating'] = llm_rate(requirements, option)
    return options

