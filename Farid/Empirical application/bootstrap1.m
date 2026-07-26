%This procedure uses a bootstrap methodology to estimate the three state
%betas distribution
%The main thing to keep in mind regarding this bootstrap is that we need to
% store a random sample of y as well as the corresponding values of z
% otherwise the sample will become meaningless. 

tic
recursions = 1000;
b = linspace(1,numel(sandp500),numel(sandp500))';
betadistrib = zeros(recursions,3);
y = sandp500;
length = prod(size(y));
z = MSI;
for i = 1:recursions
    sample = randsample(b,length,1); %we select a random sample from number 1-450 and then draw from both y and z concurrently
    yy = zeros(numel(sample),1); %these variables are required to store the random sample for y
    zz = zeros(numel(sample),1); %this will store the corresponding values for z
    for j = 1:numel(sample)
        yy(j) = y(sample(j));
        zz(j) = z(sample(j));
    end
    eqx = switchingparamse(1,yy,zz);
    betadistrib(i,:) = eqx.p(1,:)
end
toc

%the other alternative to try is to first use Z and get 3 different y's.
%Then you do a bootstrap on each one of them separately. This way you
%ensure that you get one parameter above 1 and one below 1. 