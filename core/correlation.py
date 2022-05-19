from numba import cuda, float32
import math

@cuda.jit(device=True)
def add_to_correlator(result,corrLevel,D,temp_D,C,N,A,M,corrtype):

    p = int(D.shape[1]) #number of data values in correlator level
    m = 8 #number of data values to average
    S_corr = int(D.shape[0]) #number of correlator levels

    if corrLevel >= S_corr: #S+1 correlator levels, S depends on simulation length
        return

    for j in range(1,p):
        for k in range(0,3):
            temp_D[corrLevel,j,k] = D[corrLevel,j-1,k] #temporarily store shifted data values
    
    for j in range(1,p):
        for k in range(0,3):
            D[corrLevel,j,k] = temp_D[corrLevel,j,k] #set new data values to shifted values

    for k in range(0,3):
        D[corrLevel,0,k] = result[k] #put new correlation value in 0 index

    if corrLevel == 0:
        for j in range(0,p):
            N[corrLevel,j] += 1
            if corrtype == 1: #Welford algorithm for tracking variance of correlation value (TODO: determine correct method for estimating block transformation uncertainty)
                # mean = C[corrLevel,j]/N[corrLevel,j]            #current mean of the correlated values
                stress_corr = D[corrLevel,0,0]*D[corrLevel,j,0] #new correlation value
                # delta = stress_corr - mean                      #difference of new correlation from old mean
                # mean += delta / N[corrLevel,j]                  #updated mean
                # delta2 = stress_corr - mean                     #difference of new correlation from new mean
                # variance[corrLevel,j] += delta*delta2           #updated squared distance from mean
                C[corrLevel,j] += stress_corr                  #update running sum
            if corrtype == 2:
                # mean = C[corrLevel,j]/N[corrLevel,j]
                msd = (D[corrLevel,0,0]-D[corrLevel,j,0])**2 + (D[corrLevel,0,1]-D[corrLevel,j,1])**2 + (D[corrLevel,0,2]-D[corrLevel,j,2])**2
                # delta = msd - mean
                # mean += delta / N[corrLevel,j]
                # delta2 = msd - mean 
                # variance[corrLevel,j] += delta*delta2 
                C[corrLevel,j] += msd

    else:
        for j in range(int(p/m),p):
            N[corrLevel,j] += 1
            if corrtype == 1:
                # mean = C[corrLevel,j]/N[corrLevel,j]
                # stress_corr = D[corrLevel,0,0]*D[corrLevel,j,0]
                # delta = stress_corr - mean
                # mean += delta / N[corrLevel,j]
                # delta2 = stress_corr - mean 
                # variance[corrLevel,j] += delta*delta2 
                C[corrLevel,j] += D[corrLevel,0,0]*D[corrLevel,j,0]
            if corrtype == 2:
                # mean = C[corrLevel,j]/N[corrLevel,j]
                msd = (D[corrLevel,0,0]-D[corrLevel,j,0])**2 + (D[corrLevel,0,1]-D[corrLevel,j,1])**2 + (D[corrLevel,0,2]-D[corrLevel,j,2])**2
                # delta = msd - mean
                # mean += delta / N[corrLevel,j]
                # delta2 = msd - mean 
                # variance[corrLevel,j] += delta*delta2 
                C[corrLevel,j] += msd
    
    if M[corrLevel]==0:
        A[corrLevel,0] += result[0] #only updating accumulator if counter is 0 (non-averaging method)
        A[corrLevel,1] += result[1] 
        A[corrLevel,2] += result[2]
    M[corrLevel] += 1

    
    
    return


@cuda.jit
def update_correlator(result_array,D,D_shift,C,N,A,M,corrtype):

    i = cuda.blockIdx.x*cuda.blockDim.x + cuda.threadIdx.x #chain index

    temp = cuda.local.array(3,float32)

    if i >= result_array.shape[0]:
        return

    m = 8
    S_corr = D.shape[1]
    
    for j in range(0,len(result_array[i])):
        result = result_array[i,j,:]
        if result[-1] == 1.0:
            add_to_correlator(result,0,D[i],D_shift[i],C[i],N[i],A[i],M[i],corrtype[0])
            
        for corrLevel in range(0,S_corr+1):
            if M[i,corrLevel] == m:
                # for k in range(0,3):
                #     temp[k] = A[i,corrLevel,k]/m #only used for smoothing method
                if corrtype[0] == 1: add_to_correlator(A[i,corrLevel],int(corrLevel+1),D[i],D_shift[i],C[i],N[i],A[i],M[i],corrtype[0])
                if corrtype[0] == 2: add_to_correlator(A[i,corrLevel],int(corrLevel+1),D[i],D_shift[i],C[i],N[i],A[i],M[i],corrtype[0])
                A[i,corrLevel,0] = A[i,corrLevel,1] = A[i,corrLevel,2] = 0.0
                M[i,corrLevel] = 0
    return 

@cuda.jit
def calc_corr(rawdata, calc_type, uplim, data_corr, corr_array):
    
    i = cuda.blockIdx.x*cuda.blockDim.x + cuda.threadIdx.x #chain index
    
    if i >= data_corr.shape[0]:
        return
    
    data = rawdata[0:,0:,i] #raw data for chain i
    corr = corr_array[0:,i] #store correlation values for time t and t+lag for chain i
        
    p = 8 #block transformation parameters
    m = 2 #block transformation parameters
    array_index = -1 #initialize array indexing for final results
    for k in range(0,p*m):
        array_index+=1
        corr_block(i, data, k, data_corr, array_index, corr, calc_type) #get the average correlation and error for time lag k
    for l in range(1,int(uplim)):
        for j in range(p*m**l,p*m**(l+1),m**l):
            array_index += 1
            corr_block(i, data, j, data_corr, array_index, corr, calc_type) #get the average correlation and error for time lag j
    return


@cuda.jit(device=True)
def corr_block(chainIdx, chainData, tj, corr, arr_index, xV, calc_type):
    
    #number of correlations
    n = int(len(chainData[0,0:])-tj)
    
    #begin correlation averaging for timelag tj
    xav = 0
    for r in range(0,n):
        if calc_type==1:
            xV[r] = chainData[0,r]*chainData[0,int(r+tj)] #correlation between time and time + lag
        elif calc_type == 2:
            xV[r] = (chainData[0,r]-chainData[0,int(r+tj)])**2+(chainData[1,r]-chainData[1,int(r+tj)])**2+(chainData[2,r]-chainData[2,int(r+tj)])**2
        xav+=xV[r]/n  #calculate average
    c0=(xV[0]-xav)**2   
    for r in range(1,n):
        c0+=(xV[r]-xav)**2/n
    sa=math.sqrt(c0/(n-1))
    sb=sa/math.sqrt(2*(n-1))
    n=int(math.floor(n/2))
    for r in range(0,n):
        xV[r]=(xV[2*r+1]+xV[2*r])/2
    c0=(xV[0]-xav)**2
    for r in range(1,n):
        c0=c0+(xV[r]-xav)**2
    c0=c0/n
    sap=math.sqrt(c0/(n-1))
    sbp=sap/math.sqrt(2*(n-1))
    while (math.fabs(sa-sap) > sbp+sb) and (n > 4):
        sa=sap
        sb=sbp
        n=int(math.floor(n/2))
        for r in range(0,n):
            xV[r]=(xV[2*r+1]+xV[2*r])/2
        c0=(xV[0]-xav)**2
        for r in range(1,n):
            c0=c0+(xV[r]-xav)**2
        c0=c0/n
        sap=math.sqrt(c0/(n-1))
        sbp=sap/math.sqrt(2*(n-1))
    
    corr[chainIdx,arr_index,0] = xav #set average correlation value for chain i 
    corr[chainIdx,arr_index,1] = sap #set error of average correlation value for chain i