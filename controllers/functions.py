from flask import Flask
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
import nltk
import numpy as np
import pickle
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
# from dotenv import load_dotenv
from db import db


sql_query= """
SELECT 
    article.article_id, 
    article.title, 
    article.author,
    article.publication_date, 
    article.date_added,
    article.abstract, 
    journal.journal, 
    article.keyword, 
    article_files.file_name, 
    COUNT(DISTINCT CASE WHEN logs.type = 'read' THEN 1 END) AS total_reads,
    COUNT(DISTINCT CASE WHEN logs.type = 'download' THEN 1 END) AS total_downloads,
    GROUP_CONCAT(DISTINCT CONCAT(contributors.firstname, ' ', contributors.lastname, '->', contributors.orcid) SEPARATOR ', ') AS contributors
FROM 
    article 
LEFT JOIN 
    journal ON article.journal_id = journal.journal_id 
LEFT JOIN 
    logs ON article.article_id = logs.article_id 
LEFT JOIN 
    article_files ON article.article_id = article_files.article_id
LEFT JOIN 
    contributors ON article.article_id = contributors.article_id
WHERE
    article.status = 1
GROUP BY
    article.article_id;


           """
db.ping(reconnect=True)
cursor = db.cursor()
cursor.execute(sql_query)
data = cursor.fetchall()


id = [row['article_id'] for row in data]
overviews = [row['abstract'] for row in data]
titles = [row['title'] for row in data] 

# Preprocessing
nltk.download("stopwords")
stop_words = set(stopwords.words("english"))

for n, name in enumerate(overviews):
    temp = name.lower().split(" ")
    temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
    temp = [word for word in temp if word not in stop_words]
    temp = ' '.join(temp)
    overviews[n] = temp
    
for n, title in enumerate(titles):
    temp = title.lower().split(" ")
    temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
    temp = [word for word in temp if word not in stop_words]
    temp = ' '.join(temp)
    titles[n] = temp
    
# Calculate cosine similarity
    from sklearn.feature_extraction.text import CountVectorizer

    vectorizer = CountVectorizer().fit(overviews + titles)
    # Calculate cosine similarity for overviews
    vectorizer_overviews = vectorizer.transform(overviews)
    cosine_sim_overviews = cosine_similarity(vectorizer_overviews)

    # Calculate cosine similarity for titles
    vectorizer_titles =  vectorizer.transform(titles)
    cosine_sim_titles = cosine_similarity(vectorizer_titles)
    
    article_id_to_index = {}  # Create an empty mapping
    for index, article_id in enumerate(id):
        article_id_to_index[article_id] = index
        
def get_article_recommendations( article_id, overviews_similarity_matrix, titles_similarity_matrix):
    combined_similarity = 0.4 * overviews_similarity_matrix + 0.6 * titles_similarity_matrix
    
    if article_id in article_id_to_index:
        index = article_id_to_index[article_id]
        similar_articles = combined_similarity[index]
        similar_articles = sorted(enumerate(similar_articles), key=lambda x: x[1], reverse=True)
        recommended_articles = []
        
        for i in similar_articles:
            if i[1] < 0.18:
                break
            # recommended_article_title = titles_orig[i[0]]
            # article_description = overviews_orig[i[0]]
            # recommended_articles.append({'title': recommended_article_title, 'article_id': id[i[0]], 'score': i[1]})
            
            recommended_article = {key: data[i[0]][key] for key in data[i[0]]}
            recommended_article['score'] = i[1]
            recommended_articles.append(recommended_article)


        return recommended_articles
    else:
        return ["Article ID not found in the mapping."]

 
def get_originality_score(input_title, input_abstract, isPublished=True):
    print("Checkpoint 0")

    where_condition = "WHERE status != 6"
    
    if isPublished:
        where_condition = "WHERE status = 1"
    
    sql_query = f'''
        SELECT article.article_id, article.title, article.abstract,  c.contributors 
        FROM article 
        LEFT JOIN(
            SELECT 
            	article_id, GROUP_CONCAT(DISTINCT CONCAT(firstname,' ',lastname) SEPARATOR ', ') AS contributors
 				FROM contributors GROUP BY article_id
 		) AS c ON article.article_id = c.article_id
        {where_condition}
    '''
    
    db.ping(reconnect=True)
    with db.cursor() as cursor:
        cursor.execute(sql_query)
        datas = cursor.fetchall()
        
    print("Checkpoint 1")
        
    # newIds = [row['article_id'] for row in datas]
    newOverviews = [row['abstract'] for row in datas]
    newTitles = [row['title'] for row in datas]
    
    # print(len(newIds))
    # for i in newIds:
    #     print(i)
    
    for n, name in enumerate(newOverviews):
        if len(name) != 0:
            temp = name.lower().split(" ")
            temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
            temp = [word for word in temp if word not in stop_words]
            temp = ' '.join(temp)
            newOverviews[n] = temp
        if len(newTitles[n]) != 0:
            temp = newTitles[n].lower().split(" ")
            temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
            temp = [word for word in temp if word not in stop_words]
            temp = ' '.join(temp)
            newTitles[n] = temp
    # for n, title in enumerate(newTitles):
    #     if len(title) == 0: continue
    #     temp = title.lower().split(" ")
    #     temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
    #     temp = [word for word in temp if word not in stop_words]
    #     temp = ' '.join(temp)
    #     newTitles[n] = temp
    print("Checkpoint 2")
    
    # overviews.extend(newOverviews)
    # titles.extend(newTitles)
    # id.extend(newIds)
    # for i in datas:
    #     data.append({ "article_id": i.article_id , "title": i.title, "abstract": i.abstract})
    
    # Combine the input title and abstract into a single string if needed
    # input_text = f"{input_title} {input_abstract}"
   
    input_title = input_title.lower().split(" ")
    input_title = [''.join([letter for letter in word if letter.isalnum()]) for word in input_title]
    input_title = [word for word in input_title if word not in stop_words]
    input_title = ' '.join(input_title)


    input_abstract = input_abstract.lower().split(" ")
    input_abstract = [''.join([letter for letter in word if letter.isalnum()]) for word in input_abstract]
    input_abstract = [word for word in input_abstract if word not in stop_words]
    input_abstract = ' '.join(input_abstract)
    
    newOverviews.append(input_abstract)
    newTitles.append(input_title)
    
    print("Checkpoint 3")
    
    
    overview_vectorizer = CountVectorizer().fit(newOverviews)
    vectorizer_overviews = overview_vectorizer.transform([newOverviews[-1]])
    cosine_sim_overviews = cosine_similarity(vectorizer_overviews, overview_vectorizer.transform(newOverviews[:-1]))

    
    title_vectorizer = CountVectorizer().fit(newTitles)
    vectorizer_titles = title_vectorizer.transform([newTitles[-1]])
    cosine_sim_titles = cosine_similarity(vectorizer_titles, title_vectorizer.transform(newTitles[:-1]))

    combined_similarity = (cosine_sim_overviews + cosine_sim_titles)/2
    similar_articles = sorted(enumerate(combined_similarity[0]), key=lambda x: x[1], reverse=True)
    
    similar_overviews= sorted(enumerate(cosine_sim_overviews[0]), key=lambda x: x[1], reverse=True)
    similar_titles = sorted(enumerate(cosine_sim_titles[0]), key=lambda x: x[1], reverse=True)
    
    print("Checkpoint 4")
    
    
    recommended_articles = []
    
    for (i,j,k) in zip(similar_titles, similar_overviews,similar_articles):
        if j[1] < 0.50 and i[1] < 0.50:
            break
 
        index = k[0]
        if index < len(newTitles) and index < len(newOverviews):
            recommended_article = {
                'title': datas[index]['title'],
                'abstract': datas[index]['abstract'],
                'article_id': datas[index]['article_id'],
                'contributors': datas[index]['contributors'],
                'score': {
                    'title': i[1],
                    'overview': j[1],
                    'total':k[1]
                }
                
            }
            recommended_articles.append(recommended_article)
    
    # if newOverviews:
    #     newOverviews.pop()
    print("Checkpoint 5")
    
    # if newTitles:
    #     newTitles.pop()
    return recommended_articles

def load_tokenizer(path):
    '''
        load tokenizer for abstract processing
    '''

    with open(path, 'rb') as handle:
        tokenizer = pickle.load(handle)
        
    return tokenizer

def load_label_encoder(path):
    '''
        loading label encoder for journal name processing
    '''

    with open(path, 'rb') as handle:
        label_encoder = pickle.load(handle)

    return label_encoder

def preprocess_abstract(abstract, tokenizer, label=None):
    '''
        Function to preprocess abstract before classification 

        arguments:
            abstract = raw abstract in string
            tokenizer = tokenizer used by model for training
            label = label of abstract (for testing purposes only)

        The output is an array of integer ID for each word with a maximum length of 50.
        Words are lowercased, alphanumeric characters are retained, and stopwords are removed.
        If the number of words is less than 50, the remaining spaces will be filled with zeros.
        If the number of words is greater than 50, the excess words will be truncated.

    '''
    
    ## Text Preprocessing
    abstract = abstract.lower().split(" ")
    abstract = [''.join([letter for letter in word if letter.isalnum()]) for word in abstract]
    abstract = [word for word in abstract if word not in stop_words]
    abstract = ' '.join(abstract)
    
    ## Assign unique ID to each word in the abstract
    sequences = tokenizer.texts_to_sequences([abstract])

    ## Fill with zeros or truncate the array of word IDs. The maximum length is 50.
    pad_trunc_sequences = pad_sequences(sequences, maxlen=100, padding='post', truncating='post')

    return pad_trunc_sequences, label


def classify(input_data, model, label_encoder=None):
    '''
        Function to classify processed abstract 
        arguments: 
            input_data = processed abstract
            model = A.I. model
            label_encoder = label_encoder used by model for training

        the output of the function is the journal name
    '''

    ## classify abstract using model
    output = model(input_data)

    ## Get the highest probability of classification
    output = np.argmax(output)
    print(output )

    ## Get the journal name equivalent of the output of classification
    # journal = label_encoder.inverse_transform([output])

    ## replace _ with whitespace in the journal name
    # journal = ' '.join(journal[0].split('_'))
    
    return output
    
def get_reviewer_recommendation(input_article):

    sql_query = f'''
       SELECT 
        a1.*,
        (SELECT 
            COUNT(CASE WHEN ra.accept = 1 AND ra.answer = 1 THEN 1 END)
         FROM 
            reviewer_assigned ra
         WHERE 
            ra.author_id = a1.author_id) AS total_success,
        (SELECT 
            COUNT(CASE WHEN ra.deadline < CURDATE() THEN 1 END)
         FROM 
            reviewer_assigned ra
         WHERE 
            ra.author_id = a1.author_id) AS ongoing,
        (SELECT 
            COUNT(CASE WHEN ra.deadline > CURDATE() THEN 1 END)
         FROM 
            reviewer_assigned ra
         WHERE 
            ra.author_id = a1.author_id) AS decline
        FROM 
            author a1
        LEFT JOIN 
            article a2 ON a1.author_id = a2.author_id AND a2.article_id = 189
        LEFT JOIN 
            contributors c ON a1.email_verified COLLATE utf8mb4_unicode_ci = c.email COLLATE utf8mb4_unicode_ci AND c.article_id = 189
        LEFT JOIN 
            reviewer_assigned ra2 ON a1.author_id = ra2.author_id AND ra2.article_id = 189
        WHERE 
            a1.author_id <> 1
            AND a2.article_id IS NULL
            AND c.email IS NULL
            AND (ra2.article_id IS NULL OR ra2.round <> a2.round);

    '''
    
    additional_words = ["researcher", "research","professional","master","doctor","documentation","reviewed","reviewer","masters","doctorate","thesis","dissertation","expert"]
    db.ping(reconnect=True)
    with db.cursor() as cursor:
        cursor.execute(sql_query)
        data = cursor.fetchall()

    ids = [row['author_id'] for row in data]
    field_of_expertises = [row['field_of_expertise'] for row in data]
    bios = [row['bio'] for row in data] 
    
    
    modified_bios = []
    
    for n, bio in enumerate(bios):
        if bio is None:
            modified_bios.append("")
            continue
        temp = bio.lower().split(" ")
        temp = [''.join([letter for letter in word if letter.isalnum()]) for word in temp]
        temp = [word for word in temp if word not in stop_words]
        temp = ' '.join(temp)
        modified_bios.append(temp)
        
    modified_field_of_expertises = []

    for n, field_of_expertise in enumerate(field_of_expertises):
        if field_of_expertise is None:
            modified_field_of_expertises.append("")
            continue
        parts = field_of_expertise.strip().split(",")
        processed_parts = []
        for part in parts:
            words = part.lower().strip().split() 
            processed_part = " ".join(word for word in words if word not in stop_words) 
            processed_parts.append(processed_part)
        modified_field_of_expertises.append(" ".join(processed_parts)) 
        
    
    # Joining the data
    joined_data = [field_of_expertise + " " + bio if bio is not None else None for field_of_expertise, bio in zip(modified_field_of_expertises, modified_bios,)]

    # Preprocess input_article
    input_article = input_article.lower().strip().split(" ")
    input_article = [''.join([letter for letter in word if letter.isalnum()]) for word in input_article]
    # print(input_article)
    input_article = [word for word in input_article if word not in stop_words]+additional_words
    # print(input_article)
    input_article = ' '.join(input_article)
    joined_data.append(input_article)

    # Vectorization
    vectorizer = CountVectorizer().fit(joined_data)
    vectorized_data = vectorizer.transform(joined_data).toarray()

    # Compute cosine similarity
    cosine_sim_words = cosine_similarity(vectorized_data, vectorized_data)

    # Sort similar words
    similar_words = sorted(enumerate(cosine_sim_words[-1]), key=lambda x: x[1], reverse=True)

    recommended_articles = []

    # Iterate over similar words
    for i, similarity_score in similar_words:
        if i < len(joined_data) - 1:  
            recommended_article = {key: data[i][key] for key in data[i]}
            recommended_article['score'] = similarity_score
            recommended_articles.append(recommended_article)

    return recommended_articles