%WE use the grid search on our iid variable instead of trying to find out betas using grid search
% The sample is divided into 3 sections and we analytically calculate betas
% and the RSS; the values which minimize the RSS are chosen. 
function [stats] = gridsearch2(y,z,c1,c2,intercept) %this program is for simulations only and doesn't print any output
%We define our grid in order to first split the sample into 3


count = zeros(3,1);
length = prod(size(y));
meanrevert = zeros(numel(y),1); explosive = zeros(numel(y),1); %This generates dummy variables which take a value of 1 when the relevant state occurs. 
%The following step splits the sample into 3; enabling us to calculate RSS
%separately for each. 
for i = 2:length
    if z(i)<c1
        count(2,1)=count(2,1)+1;
        meanrevert(i,1) = 1;
    elseif z(i) > c2
        count(3,1) = count(3,1)+1;
        explosive(i,1) = 1; 
    else
        count(1,1) = count(1,1)+1;
    end
end


count;

%Next we create the split samples; The Xs contain the lagged values of y
y1 = zeros(count(1,1),1); x1 = zeros(count(1,1),1);
y2 = zeros(count(2,1),1); x2 = zeros(count(2,1),1);
y3 = zeros(count(3,1),1); x3 = zeros(count(3,1),1); 
k1 = 0; k2 = 0; k3=0;

%Now we will the split samples with actual values
yret = zeros(numel(y),1);
for j = 2:length
    if z(j)<c1
        k2 = k2+1;
        y2(k2) = y(j,1)-y((j-1),1);
        x2(k2) = y(j-1,1);
        yret((j-1),1) = y(j,1)-y((j-1),1);
    elseif z(j)>c2
        k3 = k3+1;
        y3(k3) = y(j,1)-y((j-1),1);
        x3(k3) = y(j-1,1);
        yret((j-1),1) = y(j,1)-y((j-1),1);
    else
        k1 = k1+1;
        y1(k1) = y(j,1)-y((j-1),1);
        x1(k1) = y(j-1,1);
        yret((j-1),1) = y(j,1)-y((j-1),1);
    end
end


%Now we find the analytical betas that minimize each part

if intercept == 1
    mdl2 =fitlm(x2,y2,'Intercept',true);
    mdl2.Coefficients;
    mdl3 =fitlm(x3,y3,'Intercept',true);
    mdl3.Coefficients;
    const = ones(count(1,1),1);
    mdl1 = fitlm(const,y1,'Intercept',false);
    stats.beta1 = 0;    
    stats.beta2 = mdl2.Coefficients.Estimate(2,1);
    stats.beta3 = mdl3.Coefficients.Estimate(2,1);
    %stats.alpha1 = mean(y1)-stats.beta1*mean(x1);
    stats.alpha1 = mdl1.Coefficients.Estimate(1,1);
    mdl1.Coefficients;
    stats.alpha2 = mdl2.Coefficients.Estimate(1,1);
    stats.alpha3 = mdl3.Coefficients.Estimate(1,1);
   
elseif intercept == 2
    %%Put in model with dummies here
    tbl = table(y(1:(end-1)),meanrevert(2:end),explosive(2:end),y(2:end),'VariableNames',{'x','meanrevert','explosive','y'});
    x = zeros(numel(y)-1,2);
    x(:,1) = (meanrevert(2:end).*y(1:end-1));
    x(:,2) = (explosive(2:end).*y(1:end-1));
    mdl = fitlm(x,(y(2:end)-y(1:end-1)),'Intercept',true);
    mdl.Coefficients;
    stats.alpha1 = mdl.Coefficients.Estimate(1,1);
    stats.alpha2 = 0;
    stats.alpha3 = 0;
    stats.beta1 = 0;
    stats.beta2 = mdl.Coefficients.Estimate(2,1);
    stats.beta3 = mdl.Coefficients.Estimate(3,1);
    mdl.SSR;
    %mdl = fitlm(tbl,'y~x+meanrevert*x+explosive*x')

else 
    mdl2 =fitlm(x2, y2, 'Intercept',false);
    mdl3 =fitlm(x3, y3, 'Intercept',false);
    stats.beta1 = 0;    
    stats.beta2 = mdl2.Coefficients.Estimate;
    stats.beta3 = mdl3.Coefficients.Estimate; 
    stats.alpha1 = 0;
    stats.alpha2 = 0;
    stats.alpha3 = 0;
end



if intercept == 2
    p = 1;
    e = zeros(numel(y),1);
    for p = 2:prod(size(y))
        if z(p) < c1
            e(p) = yret(p-1) - stats.beta2*y(p-1)-stats.alpha1;
        elseif z(p) > c2
            e(p) = yret(p-1) - stats.beta3*y(p-1)-stats.alpha1;
        else
            e(p) = yret(p-1) - stats.beta1*y(p-1)-stats.alpha1;
        end
    end
    stats.RSS = mdl.SSR;
    %stats.RSS = sum(e.^2)
    %mdl.Coefficients.SE;
    stats.sigmae = sqrt((stats.RSS)/(numel(y)-7)); %this gives us the standard deviation of the error term;
else
    
    RSS2 = mdl2.SSR; %Residual sum of squares for mean state 1
    RSS3 = mdl3.SSR; %Residul sum of squares for state 3 - explosive
    %We calculate the RSS for the efficient state manually
    p = 1;
    e1 = zeros(count(1,1),1);
    % test = zeros(count(1,1),2); test(:,1)=y1; test(:,2)=x1;
    % test;
    for p = 1:count(1,1)
     e1(p) = yret(p,1) - stats.alpha1 - stats.beta1*x1(p);
    end

    p = 1;
    e = zeros(prod(size(y),1));
    for p = 2:prod(size(y))
         if z(p) < c1
             e(p) = yret(p-1) - stats.beta2*y(p-1) - stats.alpha2;
        elseif z(p) > c2
             e(p) = yret(p-1) - stats.beta3*y(p-1) - stats.alpha3;
         else
             e(p) = yret(p-1) - stats.beta1*y(p-1)-stats.alpha1;
         end
    end
    e;
    test2 = sum(e.^2);

    RSS1 = sum(e1.^2);
    RSS2;
    RSS3;
    %RSSother = RSS1 + RSS2 + RSS3 %This calculates the total sum of square residuals
    stats.RSS = RSS1+RSS2+RSS3;
    stats.sigmae = sqrt((stats.RSS)/(numel(y)-7)); %this gives us the standard deviation of the error term;
end
count;
end


