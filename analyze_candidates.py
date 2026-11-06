from llm_provider import LLM
import numpy as np
import json
from functools import cmp_to_key

class AnalyzeCandidates:
    def __init__(self, requirements, options):
        self.requirements = requirements
        self.options = options

    def analyze(self):
        self.options.sort(key=cmp_to_key(lambda x,y: 1 if self.compare(x,y) == 'B' else -1))

    def generate_summaries(self):
        ProductAnalyzer.init_product_analyzer(requirements=self.requirements,reference_product=self.options[0])
        for option in self.options:
            product_analyzer = ProductAnalyzer(option)
            product_analyzer.summarize_product()
            option['comparison']=product_analyzer.comparison
            option['pros_summary'] = product_analyzer.pros_summary
            option['cons_summary'] = product_analyzer.cons_summary
            option['short_summary'] = product_analyzer.short_summary
            reviews_analyzer = ReviewsAnalyzer(option)
            reviews_analyzer.summarize_reviews()
            option['reviews_summary'] = reviews_analyzer.summary

    def compare(self, productA, productB, include_reason=False):
        info_xml = f'''
Here are two products A and B. You are given the pros, cons and customer reviews of each product and also the preferences of the user.

<USER PREFERENCE>
{self.requirements['preference']}
</USER PREFERENCE>

<PRODUCT A>
<PROS>{productA['pros_summary']}</PROS>
<CONS>{productA['cons_summary']}</CONS>
<CUSTOMER REVIEWS>{productA['reviews_summary']}</CUSTOMER REVIEWS>
</PRODUCT A>

<PRODUCT B>
<PROS>{productB['pros_summary']}</PROS>
<CONS>{productB['cons_summary']}</CONS>
<CUSTOMER REVIEWS>{productB['reviews_summary']}</CUSTOMER REVIEWS>
</PRODUCT B>
'''
        prompt_with_reason='''
Decide which is the better option for the user and a brief paragraph explaining why you think so. You MUST choose either of those.
        '''
        prompt_without_reason='''
Decide which is the better option. Output ONLY A SINGLE LETTER A or B, whichever is the better option.
        '''
        prompt_for_comparison = info_xml + (prompt_with_reason if include_reason else prompt_without_reason)
        res = LLM.generate(user_prompt=prompt_for_comparison)
        return res

class ProductAnalyzer:
    fields = None
    reference = None

    @classmethod
    def init_product_analyzer(cls, requirements, reference_product):
        cls.item_name = requirements['item_name']
        cls.reference = reference_product
        prompt_for_field_generation = f'''
You are an online shopping assistant. The user wants to buy a {requirements['item_name']}.
The properties available are 
<all_properties>{reference_product['all_keys']}</all_properties>
Out of these, print a list of all the important properties that the user needs to compare to find the best product.
The output MUST be a comma separated list in the following format: property1,property2,...
        '''
        cls.fields = LLM.generate(system_prompt=prompt_for_field_generation, user_prompt=("USER PREFERENCES:\n" + requirements['preference'])).split(',')[0:10]

    def __init__(self, product_details: dict):
        self.product_details = product_details
        self.comparison = {'name': product_details['name']}

    SIMILARITY_THRESHOLD = 0.8
    def rename_details(self):
        for field in ProductAnalyzer.fields:
            if not field in self.product_details['details']:
                req_em = LLM.embed(field)
                ems = LLM.embed_batch(self.product_details['all_keys'])
                cosine_similarity = (np.dot(ems,req_em) / np.linalg.norm(ems, axis=1)) / np.linalg.norm(req_em)
                max_i = np.argmax(cosine_similarity)
                if cosine_similarity[max_i] > ProductAnalyzer.SIMILARITY_THRESHOLD:
                    self.product_details['details'][field] = self.product_details['details'][self.product_details['all_keys'][max_i]]

    def summarize_product(self):
        self.rename_details()
        system_prompt_for_comparison = f'''
You are an online shopping assistant. The user wants to buy a {ProductAnalyzer.item_name}.
You will be given the criteria and the values of the product and the reference product.
You have to compare the value with the reference value and decide whether it is ['significantly worse', 'worse', 'equal', 'better', 'significantly better'] than the reference.
Your output must STRICTLY BE OUT OF THESE FIVE VALUES.
        '''
        
        messages = []
        for field in ProductAnalyzer.fields:
            actual_value=self.product_details['details'].get(field, 'value not found')
            reference_value=self.reference['details'].get(field, 'value not found')
            user_prompt_for_comparison = f'''
<CRITERIA>{field}</CRITERIA>
<ACTUAL VALUE>{actual_value}</ACTUAL VALUE>
<REFERENCE>{reference_value}</REFERENCE>
How is the value compared to the reference?
            '''
            res = LLM.generate(system_prompt=system_prompt_for_comparison,user_prompt=user_prompt_for_comparison)
            messages.append({'role': 'user', 'content': f'for criteria \'{field}\', product value is {actual_value} vs. reference value of {reference_value}. VERDICT: product is {res} compared to reference.\n'})
            self.comparison[field] = res

        self.pros_summary = LLM.chat([*messages, {'role': 'system', 'content':  'On the basis of this conversation history, write a short paragraph describing the advantages of the product.'}])
        self.cons_summary = LLM.chat([*messages, {'role': 'system', 'content':  'On the basis of this conversation history, write a short paragraph describing the disadvantages of the product.'}])
        self.short_summary = LLM.chat([*messages, {'role': 'system', 'content':  'On the basis of this conversation history, write a short paragraph summarizing the product.'}])


class ReviewsAnalyzer:
    MERGE_CONST = 0.6
    FREQ_CONST = 1

    def __init__(self, product_details: dict):
        self.summary = ''
        self.all_pts = []
        self.all_embeddings = None
        self.all_freqs = []
        self.trusted_reviews = product_details.get('trusted_reviews', False)
        self.short_summary = product_details['short_summary']
        self.prompt_for_ingestion = f'''
You are an expert summarizer. Here is a review of a {product_details['name']}.
{self.short_summary}
Summarize the review in the form of a list of all the key points mentioned about the product STRICTLY in the following bullet format:
*text of point 1...
*text of point 2...
and so on.
        '''
        self.prompt_for_genuinity = f'''
Here is a review of a {product_details['name']}. You're an expert in detecting the genuinity of the review.
Read the review and determine whether it is genuine or fake. If it is genuine, output 'Y' else output 'N'.
        '''
        self.reviews = product_details['reviews']
        self.reviews_score = 0.0

    def summarize_reviews(self):
        for review in self.reviews:
            if self.trusted_reviews or self.is_genuine(review):
                self.ingest_review(review)
        for i in range(len(self.all_freqs)):
            if self.all_freqs[i] > ReviewsAnalyzer.FREQ_CONST:
                self.summary += self.all_pts[i] + f" [{self.all_freqs[i]} reviews]\n"
        return
        prompt_for_review_summary = f'''
Given is a summary of product details and customer reviews of a {product_details['name']}.
<DETAILS>{self.short_summary}</DETAILS>
<REVIEWS SUMMARY>{self.summary}</REVIEWS SUMMARY>
Analyze this and rate it on a scale of 0 to 100, with:
0 being 'absolute scam' to 50 being 'average' to 100 being 'the best product'
The answer MUST BE A SINGLE NUMBER BETWEEN 0 TO 100.
        '''
        sc = LLM.generate(user_prompt=prompt_for_review_summary)
        try:
            self.review_score = int(sc)
        except:
            print(f"INVALID INTEGER: {sc}")
            raise

    def is_genuine(self, review_txt):
        return ('yes' in LLM.generate(system_prompt=self.prompt_for_genuinity, user_prompt=("REVIEW: \n" + review_txt + "\nIS THIS GENUINE?"))[0].lower())

    def ingest_review(self, review_txt):
        res = LLM.generate(system_prompt=self.prompt_for_ingestion, user_prompt=("REVIEW:\n" + review_txt))
        if res[0] == '*':
            res = res[1:]
        for pt in res.split("*\n"):
            self._add_to_summary(pt)
    
    def _add_to_summary(self, pt):
        if pt.strip() == '':
            return
        embedding = LLM.embed(pt)
        embedding = embedding/np.linalg.norm(embedding)
        if self.all_embeddings is None:
            self.all_pts.append(pt)
            self.all_embeddings = [embedding]
            self.all_freqs.append(1)
            return
        all_embeddings_np = np.array(self.all_embeddings)
        cosine_similarity = np.dot(all_embeddings_np,embedding)
        if np.any(cosine_similarity < ReviewsAnalyzer.MERGE_CONST):
            self.all_freqs[np.argmax(cosine_similarity)] += 1
        else:
            self.all_pts.append(pt)
            self.all_embeddings.append(embedding)
            self.all_freqs.append(1)
    
    def get_web_reviews():
        pass



'''

JUNK CODE SECTION


comparison_xml = ''
        for key, value in self.comparison.items():
            comparison_xml += f'<{key}>{value}</{key}>\n'
        prompt_for_summary = f
Here is a description of a {ProductAnalyzer.item_name}. 
        
        LLM.generate(user_prompt=prompt_for_summary)

'''