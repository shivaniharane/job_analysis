<!DOCTYPE html>
<html>
<head>
    <title>Job Industry Analysis</title>
    <style>
        .scrolling-container {
            overflow-y: auto;
            max-height: 800px;
        }
    </style>
</head>
<body>
    <h1>Job Industry Analysis</h1>
    
    <button onclick="loadAnalysis('/job_analysis')">Job Analysis</button>
    <button onclick="loadAnalysis('/monthly_job_analysis')">Monthly Job Analysis</button>
    <button onclick="loadAnalysis('/best_company_analysis')">Best Company Analysis</button>
    <button onclick="loadAnalysis('/skill_analysis')">Skill Analysis</button>

    <!-- Container for the plots -->
    <div id="analysis-container"></div>
    <script>
        function loadAnalysis(route) {
            fetch(route)
            .then(response => response.text())
            .then(html => {
                document.getElementById('analysis-container').innerHTML = html;
            })
            .catch(err => console.log(err));
        }
    </script>
</body>
</html>
