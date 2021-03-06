
# coding: utf-8

# In[1]:

import warnings
import numpy as np

import sys
sys.path.append('/Users/jshan/Desktop/RevenueManagement')
from src import singleResource_DCM

# Calculate the displacement-adjusted revenues,
# which is to approximate the net benefit of accepting product j on resource i
# ref: function 3.15
def calc_displacement_adjusted_revenue(products, resources, static_bid_prices):
    """
    Parameter
    ----------
    products: np array
        contains products, each in the form of [name, probabilities, revenue], size n_products
    resources: np array
        contains names of resources, size n_resources
    static_bid_prices: np array
        contains static bid prices or marginal value estimates, size n_resources

    Returns
    -------
    disp_adjusted_revs: 2D np array
        contains tuples for displacement-adjusted revenues, in the form of (value, name of product),
        these are sorted from the highest value to the lowest, for each resource, size n_resources * n_products
    """


    n_resources = len(resources) # number of resources
    n_products = len(products) # number of products

    ## Constructs the incidence matrix, such that A[i][j] = 1 if product j uses resource i, 0 otherwise
    A = [[0]*n_products for _ in range(n_resources)]

    for i in range(n_resources):
        for j in range(n_products):
            if resources[i] in products[j][0]: # test if product j uses resource i
                A[i][j] = 1

    ## Calculates the sum of static bid prices for each product, over all resources it uses
    sum_static_bid_prices = [0]*n_products

    for j in range(n_products):
        for i in range(n_resources):
            if A[i][j] == 1:
                sum_static_bid_prices[j] += static_bid_prices[i]

    ## Calculates the displacement-adjusted revenues, in sorted order
    disp_adjusted_revs = [[(0, '')]*n_products for _ in range(n_resources)]

    for i in range(n_resources):
        for j in range(n_products):
            product_name = products[j][0]
            if A[i][j] == 1: # only calculates for products that uses resource i
                disp_adjusted_revs[i][j] = (int(products[j][2]) - sum_static_bid_prices[j] + static_bid_prices[i],                                             product_name)
            else:
                disp_adjusted_revs[i][j] = (0, product_name)
        disp_adjusted_revs[i].sort(key = lambda tup: tup[0], reverse=True)


    return disp_adjusted_revs


# Calculates the squared deviation of revenue within partition (l, k), for resource i
# ref: example 3.5
def calc_squared_deviation_of_revenue(i, l, k, mean_demands, disp_adjusted_revs):
    """
    Parameter
    ----------
    i: integer
        the index of the resource
    l: integer
        the starting index of the partition, i.e. the index of the first product in this partition
        product index starts from 0
    k: integer
        the ending index of the partition, i.e. the index of the last product in this partition
    mean_demands: np array
        contains mean demands of products, in the form of [product_name, mean_demand], size n_products
    disp_adjusted_revs: 2D np array
        contains tuples for displacement-adjusted revenues, in the form of (value, name of product),
        size n_resources * n_products

    Returns
    -------
    sqrd_deriv_revenue: number
        the squared deviation of revenue within the given partition
    """

    if k < l:
        warnings.warn("Wrong indices for the partition")

    if i >= len(disp_adjusted_revs):
        warnings.warn("Resource index out of boundary")

    # calculated the weighted-average displacement adjusted revenue for the given partition
    sum_demands = 0
    demands_times_disp_adjusted_rev = 0
    for j in range(l, k + 1):
        product_name = disp_adjusted_revs[i][j][1]
        product_mean_demand = float(next((v[1] for v, v in enumerate(mean_demands) if v[0] == product_name), 0))
        sum_demands += product_mean_demand
        demands_times_disp_adjusted_rev += product_mean_demand * disp_adjusted_revs[i][j][0]
    if sum_demands == 0:
        m = 0
    else:
        m = demands_times_disp_adjusted_rev / sum_demands

    sqrd_deriv_revenue = 0
    for j in range(l, k + 1):
        product_name = disp_adjusted_revs[i][j][1]
        product_mean_demand = float(next((v[1] for v, v in enumerate(mean_demands) if v[0] == product_name), 0))
        sqrd_deriv_revenue += product_mean_demand * (disp_adjusted_revs[i][j][0] - m)**2
    return sqrd_deriv_revenue


# Implement the clustering process, partition products using each resource into a group of virtual classes.
# This is done by dynamic programming, looking for the partitions that can give the minimum squared deriviation
# of revenue (i.e. total within-group variation)
# ref: section 3.4.3, example 3.5
def clustering(products, resources, disp_adjusted_revs, n_virtual_class, mean_demands):
    """
    Parameter
    ----------
    products: np array
        contains products, each in the form of [name, probabilities, revenue], size n_products
    resources: np array
        contains names of resources, size n_resources
    disp_adjusted_revs: 2D np array
        contains tuples for displacement-adjusted revenues, in the form of (value, name of product),
        size n_resources * n_products
    n_virtual_class: integer
        the number of virtual classes to partition the products into
    mean_demands: np array
        contains mean demands of products, in the form of [product_name, mean_demand], size n_products

    Returns
    -------
    paritions: np array
        consists virtual classes for every resource, each contains the names of products in that class
        size n_partition
    """

    if n_virtual_class > len(disp_adjusted_revs[0]):
        warnings.warn("More virtual classes than number of products")

    n_resources = len(resources) # number of resources
    n_products = len(products) # number of products

    # calculate the minimum total squared deviation using dynamic programming, with the formula
    # V_c(k) = min(over 1<= l <= k) {c_{lk} + V_{c-1}(l-1)}, note that k, l indexed from 1 onwards,
    # c indexed from 1 (as V_0(k) is not used).
    # indexes l, k used in calc_squared_deviation_of_revenue should start from 0

    partitions_for_resources = []
    for i in range(n_resources):
        # only partition products that uses this resource
        available_products = [j for j, k in enumerate(disp_adjusted_revs[i]) if k[0] == 0]
        if available_products:
            n_available_products = available_products[0]
        else:
            n_available_products = n_products

        if n_available_products > 0:
            # holds the minimum total squared deviation
            V = [[()]*(n_available_products +1) for _ in range(n_virtual_class)]

            # initialize V_1(k) = c_1k, for k = 1..n_virtual_class
            V[0][0] = (0, 0)
            for k in range(1, n_available_products+ 1):
                V[0][k] = (calc_squared_deviation_of_revenue(i, 0, k-1, mean_demands, disp_adjusted_revs), 0)

            # calculate V_2(k) onwards
            for c in range(1, n_virtual_class):
                for k in range(min(c + 2, n_available_products+1)):
                    V[c][k] = (0, 0)
                for k in range(c + 2, n_available_products + 1):
                    v = np.nan # record the minimum squared deviation
                    opt_l = -1 # record the starting index of the partition which gives the minimum squard deviation
                    for l in range(1, k + 1):
                        v_new = calc_squared_deviation_of_revenue(i, l-1, k-1, mean_demands, disp_adjusted_revs)                                + V[c-1][l-1][0]
                        if np.isnan(v) or v_new < v:
                            v = v_new
                            opt_l = l
                    V[c][k] = (v, opt_l - 1)

    #         print(V)
            partition_indicies = []
            c = n_virtual_class - 1
            l = n_available_products
            while True:
                start_index = V[c][l][1]
                if start_index == 0 or c == 0:
                    break
                if not partition_indicies or start_index != partition_indicies[0]:
                    partition_indicies.insert(0, start_index)
                c -= 1
                l -= 1
    #         print("indicies for partition of source ", resources[i], " is: ", partition_indicies)

            partition_indicies.append(n_available_products)
            partitions = []
            start_index = 0
            for p in range(len(partition_indicies)):
                partition = []
                names = ''
                for j in range(start_index, partition_indicies[p]):
                    if names:
                        names+=','
                    names+= disp_adjusted_revs[i][j][1]
                partition = [names]
                start_index = partition_indicies[p]
                partitions.append(partition)
        else:
            partitions = []
        print("virtual classes of products for resource ", resources[i], " is: ", partitions)

        partitions_for_resources.append(partitions)
    return partitions_for_resources

# Computes and append a probability of demand for each virtual class of products,
# which is the mean demand weighted average displacement-adjusted revenue.
# ref: section 3.4.3
def probability_of_demands(virtual_classes, mean_demands):
    """
    Parameter
    ----------
    virtual_classes: 2D np array
        contains virtual classes of products for each resource, size n_resources * n_products
    mean_demands: np array
        contains mean demands of products, in the form of [product_name, mean_demand], size n_products

    Returns
    -------
    virtual_classes: 2D np array
        consists virtual classes of products for each resource, with probability of a demand added
        size n_resources * n_products
    """

    total_demands = 0
    for product in mean_demands:
        total_demands += product[1]

    for i in range(len(virtual_classes)):
        for j in range(len(virtual_classes[i])):
            products = [x.strip() for x in virtual_classes[i][j][0].split(',')]
            mean_probability = 0
            total_probability = 0
            for product in products:
                demand = float(next((v[1] for v, v in enumerate(mean_demands) if v[0] == product), 0))
                total_probability += demand / total_demands
            mean_probability = round(total_probability / len(products), 3)
            virtual_classes[i][j].append(mean_probability)

    return virtual_classes


# Computes and append a representative revenue value for each virtual class of products,
# which is the mean demand weighted average displacement-adjusted revenue.
# ref: section 3.4.3
def representative_revenue(virtual_classes, mean_demands, disp_adjusted_revs):
    """
    Parameter
    ----------
    virtual_classes: 2D np array
        contains virtual classes of products for each resource, size n_resources * n_products
    mean_demands: np array
        contains mean demands of products, in the form of [product_name, mean_demand], size n_products
    disp_adjusted_revs: 2D np array
        contains tuples for displacement-adjusted revenues, in the form of (value, name of product),
        size n_resources * n_products

    Returns
    -------
    virtual_classes: 2D np array
        consists virtual classes of products for each resource, with representative revenue added
        size n_resources * n_products
    """
    for i in range(len(virtual_classes)):
        for j in range(len(virtual_classes[i])):
            if not virtual_classes[i][j]:
                continue
            products = [x.strip() for x in virtual_classes[i][j][0].split(',')]
            representative_rev = 0
            total_mean_demand = 0
            weighted_disp_adjusted_rev = 0
            for product in products:
                demand = float(next((v[1] for v, v in enumerate(mean_demands) if v[0] == product), 0))
                disp_adjusted_rev = float(next((v[0] for v,v in enumerate(disp_adjusted_revs[i]) if v[1]==product),0))
                total_mean_demand += demand
                weighted_disp_adjusted_rev += disp_adjusted_rev * demand
            if total_mean_demand > 0:
                representative_rev = round(weighted_disp_adjusted_rev/total_mean_demand, 3)
            virtual_classes[i][j].append(representative_rev)

    return virtual_classes

# Main function, calculates the value-function estimate for DAVN problem,
# by clustering products into virtual classes and then solving a single-resource problem
def calculate_value_function(products, resources, static_bid_prices, n_virtual_class, mean_demands, total_capacity,                              max_time, arrival_rate):
    """
    Parameter
    ----------
    products: np array
        contains products, each in the form of [name, probabilities, revenue], size n_products
    resources: np array
        contains names of resources, size n_resources
    static_bid_prices: np array
        contains static bid prices or marginal value estimates, size n_resources
    n_virtual_class: integer
        the number of virtual classes to partition the products into
    mean_demands: np array
        contains mean demands of products, in the form of [product_name, mean_demand], size n_products
    total_capacity(C): integer
        the total capacity
    max_time(T): integer
        the number of time periods
    arrival_rate: number
        the probability of arrival of a request, assumed to be constant for all time periods

    Returns
    -------
    value: 3D np array
        contains the value functions, size n_resources * (max_time + 1) * (total_capacity + 1)
    """

    # calculates the displacement-adjusted revenues
    disp_adjusted_revenue = calc_displacement_adjusted_revenue(products, resources, static_bid_prices)
    # clusters products into virtual classes
    virtual_classes = clustering(products, resources, disp_adjusted_revenue, n_virtual_class, mean_demands)

    # appends the probability of a demand and a representative revenue onto each virtual class
    probab_appended = probability_of_demands(virtual_classes, mean_demands)
    complete_classes = representative_revenue(virtual_classes, mean_demands, disp_adjusted_revenue)

    print(complete_classes)
    value_functions = []
    for i in range(len(resources)):
        # for each resource, solve a single-resource problem
        value_func = singleResource_DCM.calc_value_function(complete_classes[i], total_capacity, max_time,                                                             arrival_rate)
        value_functions.append(value_func)
#     return value_functions
    return 1



# products = [['AB', 0.5, 100], ['CD', 0.5, 100], ['ABC', 0.5, 1000], ['BCD',0.5, 1000]]
# resources =  ['AB', 'BC', 'CD']
# mean_demands = [['AB', 10.1], ['CD', 5.3], ['ABC',8], ['BCD', 9.2]]
# n_virtual_class = 3
# # static_price = [0.5, 0.5, 0.5]

# static_price = [0, 0, 0]
# # disp_adjusted_revenue = calc_displacement_adjusted_revenue(products, resources, static_price)
# calculate_value_function(products, resources, static_price, n_virtual_class, mean_demands, 4, 2, 0.5)

# products = [['AE1', 0, 220], ['AE2', 0, 150], ['AE3', 0.5, 80], ['EB1',0.2, 320],['EB2', 0.3, 220],['EB3', 0.4, 140], \
#             ['CA1', 0.14, 280],['CA2', 0.29,190],['CA3',0.43, 110], ['CAE1',0, 330],['CAE2',0.33, 260],\
#             ['CAE3',0.33, 150],['AEB1', 0.2, 420],['AEB2', 0.3, 290],['AEB3', 0.4, 190]]
# resources = ['AE', 'EB', 'CA']
# mean_demands = [['AE1', 1], ['AE2', 1], ['AE3', 1], ['EB1', 1],['EB2', 1],['EB3', 1], ['CA1', 1],['CA2', 1],\
#                 ['CA3', 1], ['CAE1', 1],['CAE2', 1],['CAE3', 1],['AEB1', 1],['AEB2', 1],['AEB3', 1]] # not given
# n_virtual_class = 3
# static_price = [0, 0, 0]# not given
# disp_adjusted = calc_displacement_adjusted_revenue(products, resources, static_price)
# print(disp_adjusted, '\n')
# print(clustering(products, resources, disp_adjusted, n_virtual_class, mean_demands))


# products = [['AB', 0.5, 100], ['CD', 0.5,100], ['ABC', 0.5, 1000], ['BCD',0.5, 1000]]

# products = [['AB', 0.5, 100], ['CD', 0.5, 100]]
# resources =  ['AB', 'BC', 'CD']
# demand = 500
# mean_demands = [['AB', demand], ['CD', demand], ['ABC',demand], ['BCD', demand]]
# n_virtual_class = 2
# static_price = [0, 0, 0]
# # disp_adjusted = calc_displacement_adjusted_revenue(products, resources, static_price)
# # print(disp_adjusted, '\n')
# # print(clustering(products, resources, disp_adjusted, n_virtual_class, mean_demands))
# value = calculate_value_function(products, resources, static_price, n_virtual_class, mean_demands, 1,1, 0.9)
# print(value)

def hahaha(a):
    print("no")
    return

def noob(s):
    return "yukai"



products = [['AB', 0.5, 100], ['CD', 0.5, 100],['ABC', 0.5, 1000], ['BCD',0.5, 1000]]
resources =  ['AB', 'BC', 'CD']
demand = 50
# mean_demands = [['AB', 10.1], ['CD', 5.3], ['ABC',8], ['BCD', 9.2], ['CDA', 3]]
mean_demands = [['AB', demand], ['CD',demand], ['ABC',demand], ['BCD', demand]]
n_virtual_class = 2
static_price = [0, 0, 0]
calculate_value_function(products, resources, static_price, n_virtual_class, mean_demands, 1, 2, 5)


# In[123]:




# In[ ]:
