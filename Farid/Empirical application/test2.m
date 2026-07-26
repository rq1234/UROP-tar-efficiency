function [parameters] = switchingparamse(c1,yy,z)
%This function finds parameters for a switching regression where one state
%is a random walk with parameter equal to 1. 
%Y is the switching series for which parameters need to be found while Z is
%the forcing variable or the sentiment index
length = prod(size(yy));
y = yy;
val = 1000; %gridspace length
iterations = (val*(val+1))/2 - val;
range = linspace(0.9,1.1,val); %this declares the range in which we look for the second and third parameter values
c1; %the random walk state
c2 = range(1); %the 2nd state (mean reverting)
c3 = range(2); %the 3rd state (explosive)
e = zeros(length,1); %the error term
parameters.p = [c1 c2 c3]; %parameter vector
parameters.minssr = 10000000000; % we have to begin by setting the sum of square residuals to a high value initially
parameters.se = zeros(1,3); %includes the standard errors of the parameters
tss = 0; %total sum of squares
ybar = mean(y);
xx = y(1:end-1).'*y(1:end-1);
xx1 = 0;
xx2 = 0;
xx3 = 0;
%% The following section finds the values which minimize the sum of squared residuals

%tic;
for i = 1:(prod(size(range))-1) %this part of the loop sets the value of the mean reverting parameter
    c2 = range(i);
    j = i+1;
    k = j;
    for k = j:(prod(size(range))) %the second loop ensures that c2 < c3 thereby reducing the number of loops
        c3 = range(k); %this sets the value of the third parameter to a value that is greater than c2
        for m = 2:length
            if z(m)<70 %criteria for mean reversion
             beta = c2;
            elseif z(m)>99 %criteria for explosivity
             beta = c3;
            else
             beta = c1; %random walk
            end
         e(m,1) = y(m)-beta*y(m-1); %this step calculates the error term
        end
        ssr = sum(e.^2); %sum of squared residuals
        if ssr<parameters.minssr %this condition checks if we need to adjust the minimum ssr value as stored in the loop
            parameters.minssr = ssr;
            parameters.p = [c1 c2 c3]; %this vector stores the parameter values where we achieve the minimum ssr
        else
            parameters.minssr = parameters.minssr;
        end
    end
end

%% This section finds the Standard error for each of the 3 parameters
count = zeros(3,1);      %this counts how many observations we have for each sub-sample
se = zeros(3,1);          %this variable stores the standard errors
er = zeros(length,1);
for n = 2:length
    if z(n) < 70         %mean reversion
        beta = parameters.p(1,2); 
        e(n,1) = (y(n)-beta*y(n-1));
        se(2,1) = (e(n,1))^2 + se(2,1); %this sums up the sum of squares of the error terms
        count(2,1) = count(2,1) + 1;
        xx2 = xx2 + y(n-1)^2;
        tss = tss + (y(n)-ybar)^2;   %total sum of squares calculation step
    elseif z(n) > 99     %explosive or second mean reverting state
        beta = parameters.p(1,3);
        e(n,1) = (y(n)-beta*y(n-1));
         se(3,1) = (e(n,1))^2 + se(3,1);
         count(3,1) = count(3,1) + 1;
         xx3 = xx3 + y(n-1)^2;
         tss = tss + (y(n)-ybar)^2;
    else                 %random walk
        beta = parameters.p(1,1);
         e(n,1) = (y(n)-beta*y(n-1));
         se(1,1) = (e(n,1))^2 + se(1,1);
         count(1,1) = count(1,1) + 1;
         xx1 = xx1 + y(n-1)^2;
         tss = tss + (y(n)-ybar)^2;
    end
end

parameters.se(1,1) = sqrt(((se(1,1)/(count(1,1)-1)))/xx1); %we next find the standard error of the regression
parameters.se(1,2) = sqrt(((se(2,1)/(count(2,1)-1)))/xx2);
parameters.se(1,3) = sqrt(((se(3,1)/(count(3,1)-1)))/xx3);


%% Diagnostics section
parameters.tstat(1,1) = parameters.p(1,1)/parameters.se(1,1); %this gives us the t-stat recall se = s^2/(X'X)
parameters.tstat(1,2) = parameters.p(1,2)/parameters.se(1,2);
parameters.tstat(1,3) = parameters.p(1,3)/parameters.se(1,3);


parameters.minssr;
rsquared = 1 - (parameters.minssr/tss);
count;
parameters.p;
%toc;
end


