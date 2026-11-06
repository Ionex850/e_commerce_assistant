import numpy as np
from llm_provider import LLM

class selector:
    K = 5

    def __init__(self, requirements, options):
        self.item_name = requirements['item_name']
        self.avg_cost = requirements['avg_cost']
        self.check_delivery_time = requirements.get('check_delivery_time',False)
        self.other_params = requirements['specs_to_check']
        self.user_info = requirements['user_info']

        self.options = options
        self.num_options = len(options)
        self.num_params = 7 + len(self.other_params)
        self.pweights = np.ones(self.num_params)
        self.pvecs = []
        self.positive_ideal = np.zeros(self.num_params)
        self.negative_ideal = np.zeros(self.num_params)
        self.topsis_scores = []

    def select(self):
        for option in self.options:
            pvec = self._gen_pvec(option)
            self.pvecs.append(pvec)
            self.positive_ideal = np.maximum(self.positive_ideal, pvec)
            self.negative_ideal = np.minimum(self.negative_ideal, pvec)
        for pvec in self.pvecs:
            d_plus = np.linalg.norm(self.positive_ideal - pvec)
            d_minus = np.linalg.norm(self.negative_ideal - pvec)
            self.topsis_scores.append(d_plus/(d_plus + d_minus))
        sorted_indices = np.argsort(self.topsis_scores)
        self.options = [self.options[i] for i in sorted_indices]
        self.pvecs = [self.pvecs[i] for i in sorted_indices]
        self.topsis_scores = [self.topsis_scores[i] for i in sorted_indices]
        return self.options[0:selector.K]
    
    def _gen_pvec(self, option):
        pvec = np.zeros(self.num_params)
        pvec[0] = option['rating']
        pvec[1] = -(option['price'])
        pvec[2] = option['discount']
        pvec[3] = -(option['price'] - self.avg_cost)
        pvec[4] = option['llm_rating']
        pvec[5] = 0 if not self.check_delivery_time else (-option.get('delivery_time', 0))
        pvec[6] = self._find_best_deal(option['offers'])
        for i in range(7,self.num_params):
          pvec[i] = option.get(self.other_params[i-7], 0)
        return pvec

    def _find_best_deal(self, offers):
        offers_xml = ''
        for i in range(len(offers)):
            offers_xml += f'<OFFER {i}>{offers[i]}</OFFER {i}>\n'
        prompt_for_best_offer = f'''
The user wants to buy a {self.item_name}. Here is the list of offers available and the necessary info about the user.
<USER INFO>
{self.user_info}
</USER INFO>
<OFFERS>
{offers_xml}
</OFFERS>

Using this information, find the best offer that the user is eligible for. Ouput ONLY THE INDEX OF THE OFFER and NOTHING ELSE.
        '''
        res = LLM.generate(user_prompt=prompt_for_best_offer)
        try:
            offer_index = int(res)
            assert offer_index < len(offers)
            return offer_index
        except:
            print(f"INVALID OFFER INDEX: {res}")
            return 0
    