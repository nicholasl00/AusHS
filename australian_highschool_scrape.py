import csv
import multiprocessing
import os
import re
import time
import timeit
import pandas as pd
# install xlrd
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
from fake_useragent import UserAgent
from selenium import webdriver
from unidecode import unidecode
from urllib.request import urlopen

# dynamic pathname based on different device, instead of hard coding the pathname
uniqueLinkList_path = os.path.join(os.getcwd(), 'UniqueLinkList.csv')
extractedData_path = os.path.join(os.getcwd(), 'ExtractedData.csv')

# Setup Chrome display
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument("--test-type")

#  Change according to the homepage of the site
Homepage = 'https://www.goodschools.com.au'

user = UserAgent().random
headers = {'User-Agent': user}


# obtaining links for all the institutions by region
def collect_institution_links(str_link):
    print("opening unique link list file")
    with open(uniqueLinkList_path, 'wt', encoding='utf-8', newline='') as Linklist:
        writer2 = csv.writer(Linklist)
        options.add_argument(f'user-agent={user}')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options,
                                  executable_path=r'C:\Users\Nicholas\Documents\Summer intern @ Seeka\chromedriver.exe')

        driver.get(str_link)
        total_link_info = ['']
        print("driver done, getting page source")
        while True:
            soup = BeautifulSoup(driver.page_source, 'lxml')
            for a in soup.find_all('div', class_='row row-padding-10'):
                for x in a.find_all('div', class_='col-md-12 clear-fix'):
                    b = x.find('a')
                    institution_link = Homepage + b['href']
                    total_link_info[0] = institution_link
                    writer2.writerow(total_link_info)
                    time.sleep(1)
            try:
                driver.find_element_by_link_text('»').click()
                print("Moving on to the next page")
                continue
            except:
                print("This is the last page")
                break


# multiprocessing structure
def multi_pool(func, input_name_list, procs):
    templist = []
    # counter = len(input_name_list)
    pool = multiprocessing.Pool(processes=procs)
    # print('Total number of processes: ' + str(procs))
    for a in pool.imap(func, input_name_list):
        templist.append(a)
        # print('Number of links left: ' + str(counter - len(templist)))
    pool.terminate()
    pool.join()
    return templist


multiple_profiles = []


# retrieving all relevant information from the institution's profile page
def collect_institution_data(str_institution_link):
    complete_school_details = {}
    global multiple_profiles
    page = requests.get(str_institution_link[0])
    soup = BeautifulSoup(page.content, 'lxml')

    # begin by getting institution name and region
    header_texts = soup.find('div', class_='school-details').find('div', class_='header').get_text()
    str_list = header_texts.split("\n")
    cleaned_h_texts = list(filter(None, str_list))
    complete_school_details['Institution Name'] = cleaned_h_texts[0].lstrip().rstrip()
    try:
        complete_school_details['Institution Region'] = cleaned_h_texts[1].lstrip().rstrip()
    except IndexError:
        complete_school_details['Institution Region'] = 0
        pass

    # save all image
    logo = soup.find('div', class_="header").find_all('img')
    div = soup.find_all('img', class_="sp-thumbnail-image")
    pic_list = []
    not_empty = True

    if not logo:
        if not div:
            not_empty = False

    if not_empty:
        institution_image_folder_path = os.path.join(os.getcwd(), 'Images')
        pic_list = logo + div
        i = 0
        for items in pic_list:
            #print(items)
            image_source = items['src']
            image = requests.get(image_source)
            institution_image_path = os.path.join(os.path.abspath(institution_image_folder_path), str(complete_school_details['Institution Name']) + "_Image_" + str(i) + ".jpg")
            #print(institution_image_path)
            with open(institution_image_path, "wb") as f:
                f.write(image.content)
                i = i + 1


    # proceed to obtain data from the top right box
    # - Sector, Government, Gender, Religion (found in some listings)
    for p_tags in soup.find('div', class_='box-content box-section-padding').find_all('p'):
        cleaned_text = p_tags.get_text().replace(" ", "").replace("\n", "")
        sorted_text = re.findall('([A-Z][a-z]*)', cleaned_text)
        complete_school_details[sorted_text[0]] = sorted_text[1]

    # obtaining data from the right mid box
    # - Principal, Addresses, Tel, Links to school's website
    for p_tags in soup.find('div', class_='box border-grey').find_all('p'):
        links = p_tags.find_all('a')
        for a in links:
            if a.get_text() == "Visit school's website":
                complete_school_details["Visit school's website"] = a['href']

        cleaned_text = p_tags.get_text().replace("\n", "")
        sorted_text = cleaned_text.split(":")
        if len(sorted_text) == 2:
            complete_school_details[sorted_text[0].lstrip().rstrip()] = sorted_text[1].lstrip().rstrip()

    #  check if school has multiple profiles
    #  - https://www.goodschools.com.au/compare-schools/in-Hawthorn-3122/scotch-college-hawthorn/boarding
    if "School Profile" in complete_school_details.keys():
        print(complete_school_details['Institution Name'] + " has multiple profiles")
        multiple_profiles.append(complete_school_details['Institution Name'])
        del complete_school_details['School Profile']

    # about us tab
    about_us_list = []
    y = soup.find('div', class_='tab-pane active').find_all('p',  recursive=False)
    for p_tags in y:
        #p_tags.get_text()
        sentences = p_tags.get_text().replace("\n", "").replace("\t", "").split(".")
        words = list(filter(None, sentences))
        for word in words:
            cleaned_sentence = word.lstrip().rstrip()
            about_us_list.append(cleaned_sentence)
    about_us_string = ". ".join(about_us_list)
    complete_school_details['About Us'] = about_us_string

    # about us - KEY FACTS section
    w = soup.find_all('div', class_='col-md-4 col-sm-4 col-xs-6 text-align-center')
    actual_list = w[:len(w)//2]
    for facts in actual_list:
        key_facts_list = []
        cleaned_text = facts.get_text().splitlines()
        words = list(filter(None, cleaned_text))
        for word in words:
            key_facts_list.append(word.lstrip().rstrip())
        final_fact_list = list(filter(None, key_facts_list))
        if len(final_fact_list) == 2:
            complete_school_details[final_fact_list[0]] = final_fact_list[1]
        if len(final_fact_list) > 2:
            complete_school_details[final_fact_list[0]] = final_fact_list[1:]
        if len(final_fact_list) == 1:
            complete_school_details[final_fact_list[0]] = "Cant retrieve data from site"

    # about us - OTHER REQUIREMENTS section
    info_1 = soup.find_all('div', class_='col-md-2 col-sm-2 col-xs-3 text-align-center') # Boarding school and offer ib
    info_2 = soup.find_all('div', class_='col-md-3 col-sm-2 col-xs-3 text-align-center')
    other_req_list = info_1[:len(info_1)//2] + info_2[:len(info_2)//2]
    for info in other_req_list:
        if info.find("div", {"class": "glyphicon glyphicon-remove"}) is not None:
            complete_school_details[info.get_text().replace("\n", "").replace("\t", "").lstrip().rstrip()] = 'No'
        else:
            complete_school_details[info.get_text().replace("\n", "").replace("\t", "").lstrip().rstrip()] = 'Yes'

    # about us - OUR CURRICULUM section
    try:
        info_1 = soup.find('div', class_='col-md-4 col-sm-4 col-xs-6 details-circle-img-box')
        info_1_cleaned = list(filter(None, info_1.get_text().splitlines()))
        final_curriculum_list = []
        for x in info_1_cleaned:
            final_curriculum_list.append(x.replace("\n", "").replace("\t", "").lstrip().rstrip())
        final_curriculum_list = list(filter(None, final_curriculum_list))
        complete_school_details[final_curriculum_list[0]] = final_curriculum_list[1:]
    except:
        pass

    # Look for the navigation tab
    navigation_tab_tags = soup.find('ul', class_='orange-nav-tabs nav nav-tabs').find_all('a')
    for tab in navigation_tab_tags:
        tab_name = tab.get_text()
        if tab_name == "Inside Scoop":
            inside_scoop_link = tab['href']
            inside_scoop_page = requests.get(inside_scoop_link)
            soup_inside_scoop = BeautifulSoup(inside_scoop_page.content, 'lxml')
            y = soup_inside_scoop.find('div', class_='tab-pane active')
            complete_school_details['Inside Scoop'] = y.get_text().replace("\n", " ").replace("\t", "").lstrip().rstrip()

        if tab_name == "Fees":  # obtaining fee link
            fee_link = tab['href']
            fee_page = requests.get(fee_link)
            soup_fee = BeautifulSoup(fee_page.content, 'lxml')
            y = soup_fee.find('div', class_='tab-pane active')  # .find_all('p', recursive=False)
            complete_school_details['Fees'] = y.get_text().replace("\n", " ").replace("\t", "").lstrip().rstrip()

        if tab_name == "Scholarship":
            final_scholarship_list = []
            scholarship_link = tab['href']
            scholarship_page = requests.get(scholarship_link)
            soup_scholarship = BeautifulSoup(scholarship_page.content,'lxml')
            y = soup_scholarship.find('div', class_='tab-pane active')
            y.p.decompose()
            info_scholarship_cleaned = list(filter(None, y.get_text().splitlines()))

            for x in info_scholarship_cleaned:
                y = x.replace("\n", " ").replace("\t", "").lstrip().rstrip()
                final_scholarship_list.append(y)
            final_scholarship_list =  list(filter(None, final_scholarship_list))
            complete_school_details["Scholarship details"] = final_scholarship_list

    if 'Head of School' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Head of School')

    if 'Headmaster' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Headmaster')

    if 'Acting Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Acting Principal')

    if 'Relieving Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Relieving Principal')

    if 'College Director' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('College Director')

    if 'College Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('College Principal')

    if 'Executive Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Executive Principal')

    if 'Co-Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Co-Principal')

    if 'School Principal' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('School Principal')

    if 'School Coordinator' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('School Coordinator')

    if 'School Head Teacher' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('School Head Teacher')

    if 'Principal/CEO' in complete_school_details:
        complete_school_details['Principal'] = complete_school_details.pop('Principal/CEO')

    if 'Principal' not in complete_school_details:
        print("Error for school ", complete_school_details)


    return complete_school_details


# https://www.goodschools.com.au/compare-schools/in-Claremont-7011/austins-ferry-primary-school
# https://www.goodschools.com.au/compare-schools/in-WaveHill-852/kalkaringi-school
# https://www.goodschools.com.au/compare-schools/in-Bargara-4670/bargara-state-school
# https://www.goodschools.com.au/compare-schools/in-Arundel-4214/ab-paterson-college
# https://www.goodschools.com.au/compare-schools/in-ManlyWest-4179/moreton-bay-boys-college

if __name__ == '__main__':

    #print("start")
    #collect_institution_links("https://www.goodschools.com.au/compare-schools/search?state=NT")
    #print("begin collecting institution data")

    #with open(uniqueLinkList_path, 'rt', encoding='utf-8', newline='') as institution_links:

    rawdata = pd.read_csv(uniqueLinkList_path)
    institution_links = rawdata.values.tolist()

    columns = ['Institution Name', 'Institution Region', 'Sector', 'Level', 'Gender', 'Principal', 'Addresses',
               "Visit school's website", 'About Us', 'School uniform', 'Number of students', 'Boarding school',
               'Offer IB', 'Accepts international students', 'Subjects overview', 'Inside Scoop', 'Fees', 'Scholarship']

    all_data = multi_pool(collect_institution_data, institution_links, 6)

    #all_data = collect_institution_data("https://www.goodschools.com.au/compare-schools/in-Fitzroy-3065/academy-of-mary-immaculate/our-story")

    print("Writing to csv file now")
    with open('institution_data.csv', 'wt', newline='') as f:
        w = csv.writer(f)
        w.writerow(columns)
        for items in all_data:
            w.writerow([items.get(col, None) for col in columns])

    if len(multiple_profiles):
        print("These are the institutions with multiple profiles " + str(multiple_profiles))

