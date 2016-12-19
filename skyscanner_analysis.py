'''
Parser of SkyScanner price alert emails
'''

import sys
import imaplib
import getpass
import re
import matplotlib.pyplot as plt    
import datetime

MONTHS=['DUMMY','January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
#'DUMMY' for adjusted indexing using datetime
MONEY_REGEXP=r'\$\d,\d{3}|\$\d{3}'
MIN_NUMBER_OF_FLIGHTS_TO_PLOT = 20
PROPORTION_CHECK = 0.7 #check validity of prices

DEPARTURE_CITY = 'Melbourne' #from SkyScanner subscription
DEFAULT_EMAIL_ACCOUNT = "oleksii.vedernikov@gmail.com"
DEFAULT_IMAP_SERVER = 'imap.gmail.com'

def process_mailbox(M):
    """
    Dumps all emails in the folder to files in output directory.
    """
    rv, data = M.search(None, "ALL")
    if rv != 'OK':
        print "No messages found!"
        return    
    #data[0].split()
    number_of_letters = len(data[0].split())
    #print number_of_letters
    for letter in data[0].split():
        #print 'l',letter
        
        rv, data = M.fetch(letter, '(RFC822)')
        if rv != 'OK':
            print "ERROR getting message", letter
            return
        print "Writing message ", letter
        f = open('mail/%s.eml' % letter, 'w')
        f.write(str(data))
        f.close()    
    return number_of_letters

def download_letters_from_email():    
    """
    Provides an access to an email folder 
    """    
    imap_server = DEFAULT_IMAP_SERVER 
    email_account = DEFAULT_EMAIL_ACCOUNT
    email_folder = "Inbox"
    
    print 'Enter password'
    password = getpass.getpass()
    M = imaplib.IMAP4_SSL(imap_server)    
    M.login(email_account, password)
    rv, data = M.select(email_folder)
    if rv == 'OK':
        print "Processing mailbox: ", email_folder
        number_of_letters = process_mailbox(M)
        M.close()
    else:
        print "ERROR: Unable to open mailbox ", rv
    M.logout()
    return number_of_letters

def process_saved_letters(files):
    """
    Making  dictionary of flights with a corresponding difference in days and price seen at this day
    """
    res={}    
    for current_file in files:  
        try:            
            f = open(current_file)
            s=f.read()
            f.close()
            prices=[]
            cities=[]
            
            for j in re.finditer(MONEY_REGEXP,str(s)):
                if 'night' not in s[j.start(0)-50:j.start(0)+50]:
                    prices.append( s[j.start(0)+1:j.end(0)].replace(',',''))            
            for j in re.finditer(r'>'+DEPARTURE_CITY+'<',str(s)):         
                cities.append(re.findall ( '<b>(.*?)</b>', s[j.end(0):j.end(0)+50], re.DOTALL)[0])
                
            dates=[]       
            current_date=[]
            i=0
            for j in re.finditer('|'.join(MONTHS),str(s)): #look up for months in the letter and extract dates:                 
                i+=1                    
                if i==1:
                    departure_month = MONTHS.index(s[j.start(0):j.end(0)])
                    departure_year = int(s[j.end(0)+1:j.end(0)+5])
                if i==3:
                    i=0                        
                    if MONTHS.index(s[j.start(0):j.end(0)])>departure_month:                         
                        current_date.append((departure_year-1,MONTHS.index(s[j.start(0):j.end(0)]),int(s[j.start(0)-3:j.start(0)-1])))
                    else:
                        current_date.append((departure_year,MONTHS.index(s[j.start(0):j.end(0)]),int(s[j.start(0)-3:j.start(0)-1])))                        
                    dates.append(current_date)
                    current_date=[]    
                else:                    
                    current_date.append((int(s[j.end(0)+1:j.end(0)+5]),MONTHS.index(s[j.start(0):j.end(0)]),int(s[j.start(0)-3:j.start(0)-1])))                
            
            if len(dates)!=len(prices) or len(prices)!=len(cities): #more prices found than dates;
                while len(prices)>len(dates):
                    prices.remove(min(prices))
                    
            for i in range(len(prices)):
                    if (cities[i],dates[i][0],dates[i][1]) not in res: #new flight alert
                        res[(cities[i],dates[i][0],dates[i][1])] = []                    
                    d1=datetime.date(dates[i][2][0],dates[i][2][1],dates[i][2][2])
                    d2=datetime.date(dates[i][0][0],dates[i][0][1],dates[i][0][2])
                    diff=str(d2-d1)   #date difference in days
                    if not( (len(res[(cities[i],dates[i][0],dates[i][1])]) > 0) and (float(prices[i])/int(res[(cities[i],dates[i][0],dates[i][1])][-1][1]) < PROPORTION_CHECK)):
                            res[(cities[i],dates[i][0],dates[i][1])].append((int(diff[:diff.find(' ')]),int(prices[i])))
        except:
            print("Unexpected error of processing letter:",current_file," with an error message:", sys.exc_info()[0])
            
    return res    

def draw_graphs(flights):    
    """
    Visualize price changes
    """
    for d in flights:
        if len(flights[d]) > MIN_NUMBER_OF_FLIGHTS_TO_PLOT:
            plt.figure(figsize=(11.69,8))            
            days_before_departure=[]
            prices=[]
            
            #creating lists of prices/days before departure
            for i in range(min([x[0] for x in flights[d]]),max([x[0] for x in flights[d]])+1):
                if i in [x[0] for x in flights[d]]:
                    for j in flights[d]:
                        if j[0]==i:
                            days_before_departure.append(j[0])
                            prices.append(j[1])
                            break
                        
            plt.scatter(days_before_departure,prices)
            plt.plot(days_before_departure,prices)    
            plt.xlim(0,max(days_before_departure))
            plt.ylim(min(prices),max(prices))
            
            plt.ylabel('Return flight price in dollars')
            plt.title('Flight from '+DEPARTURE_CITY+' to '+ d[0]+ ' on '+ str(d[1][1])+'/'+str(d[1][2])+'/'+str(d[1][0])+', return on '+ str(d[2][1])+'/'+str(d[2][2])+'/'+str(d[2][0]))
            plt.xlabel('Number of days before the flight')          
            
            plt.gca().invert_xaxis()
            plt.show()                         
                
def main():
    #choose one line from the next two to comment: 103 is for example messages, download_letters_..

    number_of_letters = 103
    #number_of_letters = download_letters_from_email() 
    
    flights = process_saved_letters(['mail/'+str(i)+'.eml' for i in range(1,number_of_letters+1)])
    draw_graphs(flights)
    
if __name__ == "__main__":
    main()
