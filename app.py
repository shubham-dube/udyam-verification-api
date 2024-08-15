from flask import Flask, jsonify, Response, make_response, request
import requests
from bs4 import BeautifulSoup
import html
import uuid
import base64
from asgiref.wsgi import WsgiToAsgi

app = Flask(__name__)
asgi_app = WsgiToAsgi(app)

udyamSessions = {}

@app.route("/api/v1/getCaptcha", methods=["GET"])
def getCaptcha():
    try:
        post_url = "https://udyamregistration.gov.in/Udyam_Verify.aspx"
        captcha_url = "https://udyamregistration.gov.in/Captcha/CaptchaControl.aspx"
        # udyamRegistrationNumber = request.json.get("udyamRegNo")
        session = requests.Session()
        id = str(uuid.uuid4())
        
        session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://udyamregistration.gov.in/Government-India/Ministry-MSME-registration.htm",
            "authority": "udyamregistration.gov.in"
        }

        response = session.get(post_url)

        htmlString = response.text
        cleaned_html_string = htmlString.replace('\n', '').replace('\r', '').replace('\t', '').replace('\\', '')
        cleaned_html_string = html.unescape(cleaned_html_string)

        soup = BeautifulSoup(cleaned_html_string, 'html.parser')

        postData = {
            "ctl00$sm": "ctl00$ContentPlaceHolder1$UpdatePaneldd1|ctl00$ContentPlaceHolder1$btnVerify",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": soup.find('input', id="__VIEWSTATE").get('value'),
            "__VIEWSTATEGENERATOR": soup.find('input', id="__VIEWSTATEGENERATOR").get('value'),
            "__VIEWSTATEENCRYPTED": soup.find('input', id="__VIEWSTATEENCRYPTED").get('value'),
            "__EVENTVALIDATION": soup.find('input', id="__EVENTVALIDATION").get('value'),
            "cmbMoreFunction": "0",
            "__ASYNCPOST": "false",
            "ctl00$ContentPlaceHolder1$btnVerify": "Verify",
        }
        loginKeys = {
            "searchKey": "ctl00$ContentPlaceHolder1$txtUdyamNo",
            "captchaKey": "ctl00$ContentPlaceHolder1$txtCaptcha",
        }

        udyamSessions[id] = {
            "session": session,
            "postData": postData,
            "loginKeys": loginKeys
        }

        captchaResponse = session.get(captcha_url)
        captchaBase64 = base64.b64encode(captchaResponse.content).decode("utf-8")

        # # For Testing Purpose only

        # imageString = f'<img src="data:image/png;base64,{captchaBase64}" alt="captcha">'
        # with open('captcha.html','w') as f:
        #     f.write(imageString)   
        #     f.close()

        # # 

        jsonResponse = {
            "sessionId": id,
            "image": "data:image/png;base64," + captchaBase64,
        }

        return jsonify(jsonResponse)
    
    except Exception as e:
        print(e)
        return jsonify({"error": "Error in fetching captcha"})
    
@app.route("/api/v1/getUdyamDetails", methods=["POST"])
def getUdyamDetails():
    try:
        post_url = "https://udyamregistration.gov.in/Udyam_Verify.aspx"
        url = "https://udyamregistration.gov.in/PrintUdyamApplication.aspx"
        
        sessionId = request.json.get("sessionId")
        udyamRegNo = request.json.get("udyamRegNo")
        captcha = request.json.get("captcha")

        user = udyamSessions.get(sessionId)
        postData = user['postData']
        loginKeys = user['loginKeys']
        postData[loginKeys['searchKey']] = udyamRegNo
        postData[loginKeys['captchaKey']] = captcha
        # print(postData)

        session = user['session']

        responseErr = session.post(
            post_url,
            data=postData
        )

        if("Udyam Registration Number does not exist" in responseErr.text):
            return jsonify({"error": "Udyam Registration Number does not exist"})
        if("Incorrect verification code. Please try again" in responseErr.text):
            return jsonify({"error": "Invalid Captcha"})

        response = session.get(url)

        htmlString = response.text
        cleaned_html_string = htmlString.replace('\n', '').replace('\r', '').replace('\t', '').replace('\\', '')
        cleaned_html_string = html.unescape(cleaned_html_string)

        soup = BeautifulSoup(cleaned_html_string, 'html.parser')

        allTables = soup.find_all('table')

        organizationTable = allTables[2]
        ORows = organizationTable.find_all('tr')

        nameOfEnterprise = ORows[0].find_all('td')[1].get_text().strip()
        organizationType = ORows[1].find_all('td')[1].get_text().strip()
        majorActivity = ORows[1].find_all('td')[3].get_text().strip()
        gender = ORows[2].find_all('td')[1].get_text().strip()
        category = ORows[2].find_all('td')[3].get_text().strip()
        dateOfIncorporation = ORows[3].find_all('td')[1].get_text().strip()
        dateOfCommencement = ORows[3].find_all('td')[3].get_text().strip()

        typeTable = allTables[3]
        TRows = typeTable.find_all('tr')

        enterpriseTypes = []
        for i in range(1,len(TRows)):
            td = TRows[i].find_all('td')

            dataYear = td[1].get_text().strip()
            classificationYear = td[2].get_text().strip()
            enterpriseType = td[3].get_text().strip()
            classificationDate = td[4].get_text().strip()

            enterpriseTypes.append({
                "dataYear": dataYear,
                "classificationDate": classificationDate,
                "classificationYear": classificationYear,
                "enterpriseType": enterpriseType
            })

        plantsTable = allTables[5]
        PRows = plantsTable.find_all('tr')

        plantsLocation = []
        for i in range(1,len(PRows)):
            td = PRows[i].find_all('td')

            unitName = td[1].get_text().strip()
            flat = td[2].get_text().strip()
            building = td[3].get_text().strip()
            town = td[4].get_text().strip()
            city = td[7].get_text().strip()
            pincode = td[8].get_text().strip()
            state = td[9].get_text().strip()
            district = td[10].get_text().strip()
            plantsLocation.append({
                "unitName": unitName,
                "flat": flat,
                "building": building,
                "town": town,
                "city": city,
                "pincode": pincode,
                "district": district,
                "state": state,
            })
        
        addressTable = allTables[7]
        ARows = addressTable.find_all('tr')
        officialAddress = {
            "addressLine1": ARows[0].find_all('td')[1].get_text() + ARows[0].find_all('td')[3].get_text()  + ARows[1].find_all('td')[1].get_text() + ARows[1].find_all('td')[3].get_text() + ARows[2].find_all('td')[1].get_text(),
            "district": ARows[3].find_all('td')[3].get_text().strip(),
            "state": ARows[3].find_all('td')[1].get_text().strip(),
        }

        mobile = ARows[4].find_all('td')[1].get_text().strip()
        email = ARows[4].find_all('td')[3].get_text().strip()

        dateOfRegistration = allTables[9].find_all('tr')[2].find_all('td')[1].get_text().strip()

        data = {
            "udyamRegNo": udyamRegNo,
            "nameOfEnterprise": nameOfEnterprise,
            "organizationType": organizationType,
            "majorActivity": majorActivity,
            "gender": gender,
            "socialCategory": category,
            "mobile": mobile,
            "email": email,
            "dateOfRegistration": dateOfRegistration,
            "officialAddress": officialAddress,
            "enterpriseTypes": enterpriseTypes,
            "dateOfCommencement": dateOfCommencement,
            "dateOfIncorporation": dateOfIncorporation,
            "plantsLocation": plantsLocation
        }

        return jsonify(data)

    except Exception as e:
        print(e)
        return jsonify({"error": "Error in fetching Udyam Registration Number Details"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(asgi_app, host='0.0.0.0', port=5001)