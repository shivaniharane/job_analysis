from flask import Flask, render_template, Response
from pymongo import MongoClient
from bson import json_util, re
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import io
import base64
import json

app = Flask(__name__)

# MongoDB connection string
mongo_uri = "mongodb+srv://ShivaniH:qwertyuiop123@cluster0.nqsvpbr.mongodb.net/"
client = MongoClient(mongo_uri)

# Connect to the 'DBS' database
db = client['DBS']
jobs_collection = db.JOBS
company_details_collection = db.Company_details
@app.route('/Company_details', methods=['GET'])
def get_company_name(company_id):
    
    company_details = company_details_collection.find_one({'company_id': company_id})
    if company_details:
        return company_details.get('name', 'Unknown')  # Default to 'Unknown' if name is not found
    else:
        return 'Unknown'
@app.route('/jobs', methods=['GET'])
def get_jobs():
    # Fetch all documents from the JOBS collection
    jobs = list(jobs_collection.find({}))
    # Use json_util to serialize the response
    return Response(json_util.dumps(jobs), mimetype='application/json')

@app.route('/')
def home():
    return render_template('home.html')

def generate_bar_plot(data):
    # Set a reasonable limit on the number of locations to show
    max_locations = 50  

    # Create a figure and a set of subplots
    fig, axes = plt.subplots(nrows=len(data), ncols=1, figsize=(10, len(data) * 10))

    if len(data) == 1:
        axes = [axes]

    for ax, (category, values) in zip(axes, data.items()):
        # Limit the number of locations to max_locations
        top_values = values[:max_locations]
        locations = [res['_id'] for res in top_values]
        counts = [res['count'] for res in top_values]

        # Use a horizontal bar chart
        ax.barh(locations, counts)
        ax.set_title(f'Job Distribution for {category}')
        ax.set_xlabel('Number of Jobs')
        ax.set_ylabel('Locations')

        
        ax.tick_params(axis='x', labelsize=8)
        ax.tick_params(axis='y', labelsize=8)

    plt.tight_layout(pad=3.0)  

    # Convert plot to a PNG image and then to a string
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return 'data:image/png;base64,{}'.format(plot_url)

@app.route('/job_analysis')
def job_analysis():
    categories = {
        "Software": re.compile(r'software|developer|engineer', re.IGNORECASE),
        "IT": re.compile(r'IT|network|system administrator', re.IGNORECASE),
        "Government": re.compile(r'government|public sector|civil service', re.IGNORECASE),
        "Healthcare": re.compile(r'healthcare|medical|hospital|doctor|nurse', re.IGNORECASE),
        "Finance": re.compile(r'finance|banking|accounting|financial', re.IGNORECASE),
        "Education": re.compile(r'education|teaching|teacher|school|college', re.IGNORECASE),
        "Retail": re.compile(r'retail|sales|store|shop', re.IGNORECASE),
        "Manufacturing": re.compile(r'manufacturing|factory|production|industrial', re.IGNORECASE),
        "Entertainment": re.compile(r'entertainment|media|film|music|television', re.IGNORECASE),
        "Sales and Marketing": re.compile(r'sales|marketing', re.IGNORECASE),
        
    }

    results = {}
    for category, regex in categories.items():
        pipeline = [
            {"$match": {"$or": [{"title": {"$regex": regex}}, {"description": {"$regex": regex}}]}},
            {"$group": {"_id": "$location", "count": {"$sum": 1}}},
            {"$limit": 12},
            {"$sort": {"count": -1}}
        ]
        category_results = list(jobs_collection.aggregate(pipeline))
        results[category] = category_results

    plot_url = generate_bar_plot(results)
    return f'<img src="{plot_url}" alt="Job Analysis Plot" style="max-width: 100%;">'

def generate_monthly_plot(data):
    structured_data = {}

    for entry in data:
        company_id = entry['_id']
        if company_id not in structured_data:
            structured_data[company_id] = {month: 0 for month in range(1, 13)}
        for month_data in entry['monthly_data']:
            month = month_data['month']
            count = month_data['count']
            structured_data[company_id][month] += count

    fig, ax = plt.subplots(figsize=(10, 6))

    sorted_companies = sorted(structured_data.items(), key=lambda item: sum(item[1].values()), reverse=True)

    for company_id, monthly_counts in sorted_companies[:20]:
        company_name = get_company_name(company_id)
        months = list(range(1, 13))
        counts = [monthly_counts.get(month, 0) for month in months]
        ax.plot(months, counts, label=f' {company_name} ({company_id})')

    ax.set_title('Monthly Job Postings by Company (Top 20 Companies)')
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Job Postings')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return 'data:image/png;base64,{}'.format(plot_url)
@app.route('/monthly_job_analysis')
def monthly_job_analysis():
    pipeline = [
        {
            "$match": {
                "company_id": {"$exists": True},
                "listed_time": {"$exists": True}
            }
        },
        {
            "$project": {
                "company_id": 1,
                "month": {"$month": "$listed_time"}
            }
        },
        {
            "$group": {
                "_id": {
                    "company_id": "$company_id",
                    "month": "$month"
                },
                "monthly_openings": {"$sum": 1}
            }
        },
        {
            "$group": {
                "_id": "$_id.company_id",
                "total_openings": {"$sum": "$monthly_openings"},
                "monthly_data": {
                    "$push": {
                        "month": "$_id.month",
                        "count": "$monthly_openings"
                    }
                }
            }
        },
        {
            "$sort": {"total_openings": -1}
        },
        {
            "$limit": 20
        }
    ]
    monthly_results = list(jobs_collection.aggregate(pipeline))
    plot_url = generate_monthly_plot(monthly_results)
    return f'<img src="{plot_url}" alt="Job Analysis Plot" style="max-width: 100%;">'

def generate_best_company_plot(data, role_type):
    # Filter data for the specific role type
    filtered_data = [item for item in data if item['_id'].get('role_type') == role_type]

    # Sort companies within the role type by average salary, handling None values
    sorted_data = sorted(
        filtered_data, 
        key=lambda x: x.get('average_max_salary', 0) or 0, 
        reverse=True
    )

    # Select the top N companies for clarity in the plot
    top_n = 20  # Adjust N as needed
    sorted_data = sorted_data[:top_n]

    # Extract company names and average salaries, replacing None with 0
    companies = [get_company_name(item['_id'].get('company_id', 'Unknown')) for item in sorted_data]
    average_salaries = [item.get('average_max_salary', 0) or 0 for item in sorted_data]

    # Create the horizontal bar plot
    fig, ax = plt.subplots(figsize=(10, 8))
    y_positions = range(len(companies))
    bars = ax.barh(y_positions, average_salaries)

    ax.set_title(f'Top {top_n} Companies for {role_type} by Average Maximum Salary')
    ax.set_xlabel('Average Maximum Salary')
    ax.set_ylabel('Company Name')  # Update the ylabel
    ax.set_yticks(y_positions)
    ax.set_yticklabels(companies)

    # Convert plot to a PNG image and then to a string
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return 'data:image/png;base64,{}'.format(plot_url)

@app.route('/best_company_analysis')
def best_company_analysis():
    pipeline = [
        {
            "$match": {
                "formatted_experience_level": {"$in": ["Entry level", "Associate", "Mid-Senior level", "Director"]}
            }
        },
        {
            "$group": {
                "_id": {
                    "company_id": "$company_id",
                    "role_type": "$formatted_experience_level"
                },
                "average_max_salary": {
                    "$avg": {
                        "$cond": [
                            {"$ne": ["$max_salary", None]},
                            "$max_salary",
                            0
                        ]
                    }
                },
                "remote_jobs_count": {
                    "$sum": {
                        "$cond": [{"$eq": ["$remote_allowed", True]}, 1, 0]
                    }
                }
            }
        },
        {
            "$sort": {"average_max_salary": -1}  # Fix the sorting field name
        }
    ]
    best_company_results = list(jobs_collection.aggregate(pipeline, allowDiskUse=True))
    plots_urls = {role_type: generate_best_company_plot(best_company_results, role_type) 
                  for role_type in ["Entry level", "Associate", "Mid-Senior level", "Director"]}

    # Construct HTML fragment with multiple plot images
    html_fragment = ''.join(f'<h3>{role_type}</h3><img src="{url}" alt="Plot for {role_type}" style="max-width: 100%;">' 
                            for role_type, url in plots_urls.items())

    return html_fragment

@app.route('/skill_analysis')
def skill_analysis():
    hardcoded_skills = ['Java', 'Project Management', 'HTML', 'CSS', 'SEO', 'Sales', 'Marketing', 'Networking', 'communication', 'agile', 'jira', 'git', 'testing', 'Springboot', 'MS Office Suite', 'Microsoft Office', 'excel', 'word', 'Python', 'JavaScript', 'SQL', 'Data Analysis', 'Machine Learning']

    # Fetch all unique company names
    all_company_ids = set()
    for skill in hardcoded_skills:
        regex_query = {'description': {'$regex': skill, '$options': 'i'}}
        matching_jobs = jobs_collection.find(regex_query)
        company_ids = [job.get('company_id', 'Unknown') for job in matching_jobs]
        all_company_ids.update(company_ids)

    # Create a mapping of company_id to company_name
    company_name_mapping = {company_id: get_company_name(company_id) for company_id in all_company_ids}

    # Prepare data for plotting
    skill_plot_urls = {}
    for skill in hardcoded_skills:
        regex_query = {'description': {'$regex': skill, '$options': 'i'}}
        matching_jobs = jobs_collection.find(regex_query)

        company_labels = []
        max_salaries = []
        for job in matching_jobs:
            company_id = job.get('company_id', 'Unknown')
            company_name = company_name_mapping.get(company_id, 'Unknown')  # Use the pre-fetched mapping
            max_salary = job.get('max_salary', 0)
            company_labels.append(str(company_name))
            max_salaries.append(max_salary / 10)

        max_salaries, company_labels = zip(*sorted(zip(max_salaries, company_labels), reverse=True))

        company_labels = company_labels[:1]
        max_salaries = max_salaries[:1]

        skill_plot_urls[skill] = {'company_labels': company_labels, 'max_salaries': max_salaries}

    plt.figure(figsize=(15, 10))
    for skill, data in skill_plot_urls.items():
        plt.barh(data['company_labels'], data['max_salaries'], label=skill)

    plt.xlabel('Max Salary (in K)')
    plt.ylabel('Company')
    plt.title('Top 1 Salary Distribution for Various Skills')
    plt.legend()
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    return f'<img src="data:image/png;base64,{plot_url}" alt="Combined Plot" style="max-width: 100%;">'
if __name__ == '__main__':
    app.run(debug=True)
