import requests
from bs4 import BeautifulSoup as bs

def search_image(list):
    attraction_list = list
    attraction_image = []

    for attraction in attraction_list:
        search_term = attraction
        params = {"q": search_term,
                "tbm": "isch"}

        html = requests.get("https://www.google.com/search", params=params, timeout=10)

        soup = bs(html.content)
        image = soup.select('div img')

        image_url = image[1]['src']
        attraction_image.append(image_url)

        image_dict = dict(zip([attraction for attraction in list], attraction_image))

    return image_dict

"""
Alternative: This produces HQ images but causes the app to be super slow.

def search_image(list):
    attraction_list = list
    attraction_image = []

    for attraction in attraction_list:
        search_term = attraction

        html = requests.get(f"https://source.unsplash.com/400x300/?{search_term}").content
        attraction_image.append(html)

        image_dict = dict(zip([attraction for attraction in list], attraction_image))

    return image_dict
"""