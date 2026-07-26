%In this script we use a gridsearch in order to look for values of the
%exogenous varible Z that minimize the RSS and enable us to find the
%relevant betas. This will tell us how much of the time the variable spends
%in the 3 different states, respectively.
gridlength = 200;
min = 10; max = 70; %these have to be carefully chosen and depend on the data at hand; for S&P500 use 10 70 - for FTSE100 use 
grid = linspace(min,max,gridlength);
minssr = 10e10;
intercept = 2; % intercept = 0 for no drift; intercept = 1 for switching drift; intercept = 2 for constant drift.
y = log(sp500daily(2:end)); %2 lags for FTSE100 and 1 lag for S&P500
z =  vixsp500(1:6399);
for i = 1:(gridlength-1)
    c1 = grid(i)
    for j = i:(gridlength-6)
        c2 = grid(j+6);
        statistics = gridsearchret(y,z,c1,c2,intercept);
        if statistics.RSS < minssr
            minssr = statistics.RSS;
            data = statistics;
            c1min = c1; c2min = c2;
        else
            minssr = minssr;
        end
    end
    minssr;
    
end

data
c1min
c2min
