from numba import cuda
import math

from numba.cuda.random import xoroshiro128p_uniform_float64, xoroshiro128p_normal_float64


@cuda.jit
def fill_uniform_rand(rng_states, nchains, count, uniform_rand):
    '''
    GPU kernel to fill array with random uniform values in uniform_rand for each chain
    '''

    i = cuda.grid(1)

    if i >= nchains:
        return

    for j in range(0, count):
        x = 0.0
        while x == 0.0: #do not include 0 in uniform random numbers
            x = xoroshiro128p_uniform_float64(rng_states, i)

        uniform_rand[i,j] = x

    return

@cuda.jit
def refill_uniform_rand(rng_states, nchains, count, uniform_rand):
    '''
    GPU kernel to refill all used random values in uniform_rand for each chain
    '''

    i = cuda.grid(1)

    if i >= nchains:
        return

    for j in range(0, int(count[i])):
        x = 0.0
        while x == 0.0: #do not include 0 in uniform random numbers
            x = xoroshiro128p_uniform_float64(rng_states, i)

        uniform_rand[i,j] = x

    count[i] = 0.0

    return


@cuda.jit
def fill_gauss_rand_tauCD(rng_states, discrete, nchains, count, SDtoggle, CD_flag, gauss_rand, pcd_array, pcd_table_eq, pcd_table_cr, pcd_table_tau):
    '''
    GPU kernel to fill random values from a guassian distribution in gauss_rand array
    '''
    i = cuda.grid(1)

    if i>=nchains:
        return

    for j in range(0,count):
        x = 0.0
        while x == 0.0: #do not include 0 in uniform random numbers
            x = xoroshiro128p_uniform_float64(rng_states, i)

        if CD_flag == 1 and discrete==True:

            if SDtoggle==True:
                gauss_rand[i,j,3] = tau_CD_eq(x, pcd_table_eq, pcd_table_tau)
            else:
                gauss_rand[i,j,3] = tau_CD_cr(x, pcd_table_cr, pcd_table_tau)

        elif CD_flag == 1 and discrete == False:

            if SDtoggle==True:
                gauss_rand[i,j,3] = tau_CD_f_t(x,pcd_array[6],pcd_array[8],pcd_array[7],pcd_array[5],pcd_array[0])
            else:
                gauss_rand[i,j,3] = tau_CD_f_d_t(x,pcd_array[9],pcd_array[10],pcd_array[11],pcd_array[12],pcd_array[5])

        else:
            gauss_rand[i,j,3] = 0.0
            gauss_rand[i,j,3] = 0.0

        for k in range(0,3):
            gauss_rand[i,j,k] = xoroshiro128p_normal_float64(rng_states, i)

    return

@cuda.jit
def refill_gauss_rand_tauCD(rng_states, discrete, nchains, count, SDtoggle, CD_flag, gauss_rand, pcd_array, pcd_table_eq, pcd_table_cr, pcd_table_tau):
    '''
    GPU kernel to refill all used random values from the gauss_rand array
    '''
    i = cuda.grid(1)

    if i>=nchains:
        return

    for j in range(0,int(count[i])):
        x = 0.0
        while x == 0.0: #do not include 0 in uniform random numbers
            x = xoroshiro128p_uniform_float64(rng_states, i)

        if CD_flag == 1 and discrete == True:

            if SDtoggle==True:
                gauss_rand[i,j,3] = tau_CD_eq(x, pcd_table_eq, pcd_table_tau)
            else:
                gauss_rand[i,j,3] = tau_CD_cr(x, pcd_table_cr, pcd_table_tau)

        elif CD_flag == 1 and discrete == False:

            if SDtoggle==True:
                gauss_rand[i,j,3] = tau_CD_f_t(x,pcd_array[6],pcd_array[8],pcd_array[7],pcd_array[5],pcd_array[0])
            else:
                gauss_rand[i,j,3] = tau_CD_f_d_t(x,pcd_array[9],pcd_array[10],pcd_array[11],pcd_array[12],pcd_array[5])

        else:
            gauss_rand[i,j,3] = 0.0
            gauss_rand[i,j,3] = 0.0

        for k in range(0,3):
            gauss_rand[i,j,k] = xoroshiro128p_normal_float64(rng_states, i)

    count[i] = 0.0

    return


@cuda.jit(device=True)
def tau_CD_cr(p, pcd_table_cr, pcd_table_tau):
    '''
    Device function to calculate probability of creation due to CD using discrete pCD modes
    '''

    for i in range(0,len(pcd_table_cr)):

        if pcd_table_cr[i] >= p:

            return 1.0/pcd_table_tau[i]


@cuda.jit(device=True)
def tau_CD_eq(p, pcd_table_eq, pcd_table_tau):
    '''
    Device function to calculate probability of creation due to SD using discrete pCD modes
    '''
    for i in range(0,len(pcd_table_eq)):

        if pcd_table_eq[i] >= p:

            return 1.0/pcd_table_tau[i]
        

@cuda.jit(device=True)
def tau_CD_f_d_t(prob,d_Adt,d_Bdt,d_Cdt,d_Ddt,d_tau_D_inverse):

    if prob < d_Bdt:
        return math.pow(prob*d_Adt + d_Ddt,d_Cdt) 
    else:
        return d_tau_D_inverse 

@cuda.jit(device=True)
def tau_CD_f_t(prob,d_At,d_Ct,d_Dt,d_tau_D_inverse,d_g):

    if prob < 1.0 - d_g:
        return math.pow(prob * d_At + d_Dt,d_Ct) 
    else:
        return d_tau_D_inverse 
