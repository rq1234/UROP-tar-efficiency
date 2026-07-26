%In this script we use a gridsearch in order to look for values of the
%exogenous varible Z that minimize the RSS and enable us to find the
%relevant betas. This will tell us how much of the time the variable spends
%in the 3 different states, respectively.
gridlength = 100; %grid length should be sparse if the sample size is not large enough
min = -1.49; max = 1.30; %minimum and maximum values for the surprise or ADS index
grid = linspace(min,max,gridlength);
minssr = 10e+10;
intercept = 0; %This specifies whether we want an intercept or not
y = log(COPPER(327:end));
z = ADSIndex(325:700);
for i = 1:(gridlength-1)
    c1 = grid(i);
    for j = i:(gridlength-4)
        c2 = grid(j+4);
        statistics = gridsearchsurp(y,z,c1,c2,intercept);
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
