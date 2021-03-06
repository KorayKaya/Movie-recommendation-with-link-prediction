import Graph_Amazon_Movies as gam
import Amazon_Movie_Parser as prs
import numpy as np
import pandas as pd
from networkx.algorithms import bipartite
import networkx as nx
import Amazon_Movie_Parser as prs
import datetime
from numpy import savetxt
import Computations_debug as comp
import random
from sklearn import metrics
from sklearn.metrics import roc_auc_score
from sklearn.metrics import roc_curve

class Amazon:
    def __init__(self, debug_mode = 'Off'):
        self.debug_mode = debug_mode
        self.n_movies_model = 20000
        self.n_movies_validation = 20000
        self.walk_steps = 20
        self.beta=0.15
        self.top_neighbor = 60
        self.n_test_users = 100
        self.threshold = 10
        self.start_index_v = 100000
        self.file_name = 'data/movies.txt'
        self.top_N_movie_suggestions = 10
        self.file_type = 'txt'
        
    def show_parameters_in_use(self):
        lst_params_name = ['debug_mode', 'n_movies_model', 'n_movies_validation', 'walk_steps', 'beta', 
                          'top_neighbor', 'n_test_users', 'threshold', 'start_index_v', 'file_name', 
                           'top_N_suggestions']
        
        lst_params_value = [self.debug_mode, self.n_movies_model, self.n_movies_validation, self.walk_steps, self.beta, 
                          self.top_neighbor, self.n_test_users, self.threshold, self.start_index_v, self.file_name, 
                           self.top_N_movie_suggestions]
        
        lst_params_info = ['Set it On if you want to see more logs', 
                           'Number of movies in the 1st data-set. Used for P matrix generation.', 
                           'Number of movies in the 2nd data-set. This data-set will be used to verify how accurately we can predict an edge between a user and a movie.', 
                           'How many steps we walk? How many iterations we do?', 
                           'Constant Beta value used in random walk calculations', 
                           'How many neighbors (similar users) we need to pick for calculations? These are the top users having the best probability value in the P matrix after N number of walks.',
                           'How many users should we use for the evaluation. In other words, i.e. we will pick N number user, predict their new edges and see how successfull we are. We will not do the calculation for all users because it is too many, we will not do it fot only 1 user, because it is not reliable..',
                           'What is the threshold to use for the accuracy calculations. This is actually not quite necessary since we will use auc and see the different auc_score threshold values.',
                           'This indicates from which review we should start generating our 2nd graph. This will generally be equal to the n_movies_model parameter but it is possible to pick another number.',
                           'From which path we read our movies.txt file having the Amazon reviews in it.',
                           'How many new movies will be suggested to the user?']
        
        dict_params ={'Name': lst_params_name, 'Value': lst_params_value, 'Info': lst_params_info}

        df_params = pd.DataFrame(dict_params)
        #print(df_params)
        
        return df_params
        

    def create_graphs(self, file_name, n_movies, n_movies_v, start_index_v):
        # >>>>>>>>>>>  Preprocessing  <<<<<<<<<<<<<<<
        # >>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<
        start_time = datetime.datetime.now()
        
        self.file_name = file_name
        self.n_movies_model = n_movies
        self.n_movies_validation = n_movies_v
        self.start_index_v = start_index_v
        
        print('*************** 1st Graph calculations - MODEL *************** ')
        grpComp = comp.GraphComp()

        grp = gam.Graph_Amazon()
        #file_name='data/movies.txt'; n_movies=40000; 
        prs_out='dictionary'

        max_connected_gr_amazon_movies = grpComp.Create_Bipartite_Giant_Component(grp, file_name, n_movies, prs_out, self.file_type)

        bottom_nodes, top_nodes = bipartite.sets(max_connected_gr_amazon_movies)

        grpComp.health_check(grp, max_connected_gr_amazon_movies, bottom_nodes, top_nodes)
        
        end_time = datetime.datetime.now()
        print('Calculation time-1st Part: {}'.format(end_time-start_time))

        print('\n*************** 2nd Graph calculations - TEST *************** ')
        start_time = datetime.datetime.now()
        grpComp_v = comp.GraphComp()
        grp_v = gam.Graph_Amazon()
        # start_index_v >> here index means record, in reality index=9*start_index
        #file_name_v='data/movies.txt'; start_index_v=40000; n_movies_v=5000; prs_out_v='dictionary'
        file_name_v=file_name; prs_out_v='dictionary'

        max_connected_gr_amazon_movies_VAL = \
        grpComp_v.Create_Bipartite_Giant_Component_VAL(grp_v, file_name_v, start_index_v, n_movies_v, prs_out_v, self.file_type)

        bottom_nodes_v, top_nodes_v = bipartite.sets(max_connected_gr_amazon_movies_VAL)

        grpComp_v.health_check(grp_v, max_connected_gr_amazon_movies_VAL, bottom_nodes_v, top_nodes_v)
    
        n_movies = len(list(top_nodes)); n_movies_v = len(list(top_nodes_v))
        n_users = len(list(bottom_nodes)); n_users_v = len(list(bottom_nodes_v))
        print('n_movies for modeling (P matrix) = {} .. n_movies for testing = {}'.format(n_movies, n_movies_v))
        print('n_users for modeling (P matrix) = {} .. n_users for testing = {}'.format(n_users, n_users_v))
        total_edges = len(max_connected_gr_amazon_movies.edges)
        total_edges_v = len(max_connected_gr_amazon_movies_VAL.edges)
        print('Avg degree (edge) per user in MODELING GRAPH: {}  ... in TEST GRAPH: {}'.format(total_edges/n_users, total_edges_v/n_users_v))
        
        end_time = datetime.datetime.now()
        print('Calculation time-2nd Part: {}'.format(end_time-start_time))

        return max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL
    
    def run_validation(self, max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, walk_steps, n_test_users, beta, top_neighbor):
        start_time = datetime.datetime.now()
        
        self.walk_steps = walk_steps
        self.beta = beta
        self.top_neighbor = top_neighbor
        self.n_test_users = n_test_users
        threshold = self.threshold

        grp = gam.Graph_Amazon(); grpComp = comp.GraphComp(); grpComp_v = comp.GraphComp()
        #grp = gam.Graph_Amazon(); grpComp = comp.GraphComp(debug_mode='On'); grpComp_v = comp.GraphComp(debug_mode='On')

        print('Preparation starts at {}'.format(datetime.datetime.now()))
        bottom_nodes, top_nodes = bipartite.sets(max_connected_gr_amazon_movies)
        bottom_nodes_v, top_nodes_v = bipartite.sets(max_connected_gr_amazon_movies_VAL)
        
        P_norm = grpComp.Generate_P_Matrix_only(max_connected_gr_amazon_movies, bottom_nodes, top_nodes)
        print('P_norm is generated: {}'.format(datetime.datetime.now()))

        n_nodes = len(max_connected_gr_amazon_movies.nodes); n_nodes_v = len(max_connected_gr_amazon_movies_VAL.nodes)
        n_movies = len(list(top_nodes)); n_users = len(list(bottom_nodes))
        n_movies_v = len(list(top_nodes_v)); n_users_v = len(list(bottom_nodes_v))

        node_list = list(max_connected_gr_amazon_movies.nodes); node_list_v = list(max_connected_gr_amazon_movies_VAL.nodes)
        top_node_list = list(top_nodes); top_node_list_v = list(top_nodes_v); 

        movie_indexes, user_indexes = grpComp.movie_user_indexes(node_list, top_node_list)
        movie_indexes_v, user_indexes_v = grpComp_v.movie_user_indexes(node_list_v, top_node_list_v)

        # pick some users to test randomly
        #test_users = random.sample(bottom_nodes, k = n_test_users)

        # what if we pick randomly from common users? (instead of selecting the test users from the old dataset)
        lst_common_users = list(set(bottom_nodes) - (set(bottom_nodes) - set(bottom_nodes_v)))
        lst_common_movies = list(set(top_nodes) - (set(top_nodes) - set(top_nodes_v)))
        test_users = random.sample(lst_common_users, k = n_test_users)

        # a table test_users * new_movies (movies in the new dataset-can also exist in the first dataset)
        # but obviously the edges are totally new in the new dataset
        lst_users = []
        lst_movies = []
        lst_predict = []
        lst_real = []
        lst_ratios = []
        lst_total_reviews_for_movies = []
        lst_total_reviews_for_movies_old = []
        lst_total_reviews_for_movies_new = []
        lst_total_OLD_edges_for_users = []
        lst_total_NEW_edges_for_users = []

        # test a single user
        #test_users = ['A15BIF2J5V7IHZ']

        print('FOR loop starts in top-K users: {}'.format(datetime.datetime.now()))
        movie_FOR_reference_user = list(top_nodes_v)
        
        # test_users are the users we will predict their future movies
        for i, user in enumerate(test_users):
            ref_user_idx = node_list.index(user) 
            R = np.zeros(n_nodes); R[ref_user_idx] = 1
            R_zero = R.copy()
            movie_FOR_reference_user_unique = movie_FOR_reference_user.copy()
            
            # we shouldn't check a movie which has already been reviewed by the user
            for mv in lst_common_movies:
                try:
                    if max_connected_gr_amazon_movies.has_edge(user, mv):
                        movie_FOR_reference_user_unique.remove(mv)
                except:
                    if self.debug_mode == 'On':
                        print('Movie {} has not been reviewed by user {} in the first (modeling) dataset.'.format(mv, user))
            
            # let's see it for the last user, too: n_test_users - 1
            if i % 10 == 0 or i == n_test_users - 1:
                print('{}. of {} Random walk starts for {}-{} at {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))
            
            if self.debug_mode == 'On':
                print('{}. Random walk starts for {}-{} at {}'.format(i, ref_user_idx, user, datetime.datetime.now()))
            #R_vector = grpComp.random_walk_vector(P_norm, R[ref_user_idx], R_zero[ref_user_idx], beta=beta, n_steps=walk_steps)
            R_vector = grpComp.random_walk_vector(P_norm, R, R_zero, beta=beta, n_steps=walk_steps)

            '''
            # similarity_check_vector_VAL is doing the entire check for both the modeling dataset and the new dataset
            # a user can have an edge in the new dataset, too. since we predict 1 user-movie connection at a time,
            # we use the new data, as well. this approach is open to the discussion.
            # if we consider a missing edge, this approach should be fine but if we totally need to find ALL edges at once,
            # then we shouldn't consider the new edges in calculations
            # so we don't do re-modeling from scratch but we take advantage of the existing (new) edges to evaluate
            df_summary, movie_list_ref, movie_by_reference_user, similar_users = \
            grpComp.similarity_check_vector(R_vector, max_connected_gr_amazon_movies, movie_indexes,\
                                            ref_user_idx, node_list, top_similarity = top_neighbor)
            '''

            if self.debug_mode == 'On':
                print('similarity_check_vector_VAL starts for {}-{} at {}'.format(ref_user_idx, user, datetime.datetime.now()))
            ### check below if needed.. or if above needed..
            df_summary_v, movie_list_ref_v, movie_by_reference_user_v, user_similarity_top_non_zero = \
            grpComp_v.similarity_check_vector_VAL(R_vector, movie_indexes, ref_user_idx, node_list, node_list_v, \
            movie_FOR_reference_user_unique, max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, top_similarity=top_neighbor)

            self.df_summary_v = df_summary_v
            
            '''
            # this is to see the ratio in the modeling dataset, not required for the prediction phase
            # but can be checked to see the performance in the modeling dataset
            df_summary_ratio = \
            grpComp.similarity_summary_ratio(df_summary, movie_list_ref, max_connected_gr_amazon_movies, \
                                             movie_by_reference_user)
            '''

            if self.debug_mode == 'On':
                print('similarity_summary_ratio_VAL starts for {}-{} at {}'.format(ref_user_idx, user, datetime.datetime.now()))

                print('**********************************************')
            
            df_summary_ratio_v = \
            grpComp_v.similarity_summary_ratio_VAL(df_summary_v, movie_list_ref_v, \
                                     max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL)
            self.df_summary_ratio_v = df_summary_ratio_v
            
            #print(self.df_summary_ratio_v)
            
            # let's see it for the last user, too: n_test_users - 1
            if i % 10 == 0 or i == n_test_users - 1:
                print('Calculate the ratios per movie: {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))

            if self.debug_mode == 'On':
                print('Calculate the ratios per movie: {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))
                
            # we will iterate in the new movies
            for mv_new in movie_FOR_reference_user_unique:
                # ratio in the summary view for a specific movie (will always return 1 record since we give the mean 
                # in the summmary view, so values[0])
                ratio_m = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[1]

                # how many times this movie reiewed 
                review_m = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[2]
                
                # how many times this movie reiewed - in the OLD (modeling) dataset
                review_m_old = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[3]
                
                # how many times this movie reiewed - in the NEW (TEST) dataset
                review_m_new = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[4]

                lst_users.append(user)
                lst_movies.append(mv_new)
                predict_calc = 1 if ratio_m > threshold else 0
                lst_predict.append(predict_calc)
                real_m = max_connected_gr_amazon_movies_VAL.has_edge(user, mv_new)
                lst_real.append(1 if real_m==True else 0)
                lst_ratios.append(ratio_m)
                lst_total_reviews_for_movies.append(review_m)
                lst_total_reviews_for_movies_old.append(review_m_old)
                lst_total_reviews_for_movies_new.append(review_m_new)
                edge_old = len(max_connected_gr_amazon_movies.edges(user))
                edge_new = len(max_connected_gr_amazon_movies_VAL.edges(user))
                lst_total_OLD_edges_for_users.append(edge_old)
                lst_total_NEW_edges_for_users.append(edge_new)

            #df_summary_ratio_v_TOPN = df_summary_ratio_v.sort_values(by='ngbr_ratio', ascending=False).head(top_N_suggestions)
                                
        grpComp_v.movie_user_compare_datasets(top_nodes_v, top_nodes, bottom_nodes_v, bottom_nodes)

        dict_FINAL = {'user': lst_users, 'movie': lst_movies, 'prediction': lst_predict, 'reality': lst_real, 
                        'ngbr_ratio': lst_ratios, 'tot_rev_m': lst_total_reviews_for_movies, 
                      'tot_rev_m_OLD': lst_total_reviews_for_movies_old, 'tot_rev_m_NEW': lst_total_reviews_for_movies_new,
                      'n_old_edge': lst_total_OLD_edges_for_users, 'n_new_edge': lst_total_NEW_edges_for_users}

        df_FINAL = pd.DataFrame(dict_FINAL)
        
        end_time = datetime.datetime.now()
        print('**********************************************')
        print('Calculation time for ALL-Predictions: {}'.format(end_time-start_time))

        # save the necessary info to files to avoid repeating the calculations - PART-1
        # max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, P_norm
        '''
        MovieGraph_1 = nx.to_numpy_matrix(max_connected_gr_amazon_movies)
        MovieGraph_1_val = nx.to_numpy_matrix(max_connected_gr_amazon_movies)

        from tempfile import TemporaryFile
        outfile_MovieGraph_1 = TemporaryFile()
        '''
        
        return df_FINAL
    
    def run_validation_TOP_N(self, max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, walk_steps, n_test_users, beta, top_neighbor, top_N_suggestions):
        start_time = datetime.datetime.now()
        
        self.walk_steps = walk_steps
        self.beta = beta
        self.top_neighbor = top_neighbor
        self.n_test_users = n_test_users
        threshold = self.threshold
        self.top_N_movie_suggestions = top_N_suggestions

        grp = gam.Graph_Amazon(); grpComp = comp.GraphComp(); grpComp_v = comp.GraphComp()
        #grp = gam.Graph_Amazon(); grpComp = comp.GraphComp(debug_mode='On'); grpComp_v = comp.GraphComp(debug_mode='On')

        print('Preparation starts at {}'.format(datetime.datetime.now()))
        bottom_nodes, top_nodes = bipartite.sets(max_connected_gr_amazon_movies)
        bottom_nodes_v, top_nodes_v = bipartite.sets(max_connected_gr_amazon_movies_VAL)
        
        P_norm = grpComp.Generate_P_Matrix_only(max_connected_gr_amazon_movies, bottom_nodes, top_nodes)
        print('P_norm is generated: {}'.format(datetime.datetime.now()))

        n_nodes = len(max_connected_gr_amazon_movies.nodes); n_nodes_v = len(max_connected_gr_amazon_movies_VAL.nodes)
        n_movies = len(list(top_nodes)); n_users = len(list(bottom_nodes))
        n_movies_v = len(list(top_nodes_v)); n_users_v = len(list(bottom_nodes_v))

        node_list = list(max_connected_gr_amazon_movies.nodes); node_list_v = list(max_connected_gr_amazon_movies_VAL.nodes)
        top_node_list = list(top_nodes); top_node_list_v = list(top_nodes_v); 

        movie_indexes, user_indexes = grpComp.movie_user_indexes(node_list, top_node_list)
        movie_indexes_v, user_indexes_v = grpComp_v.movie_user_indexes(node_list_v, top_node_list_v)

        # pick some users to test randomly
        #test_users = random.sample(bottom_nodes, k = n_test_users)

        # what if we pick randomly from common users? (instead of selecting the test users from the old dataset)
        lst_common_users = list(set(bottom_nodes) - (set(bottom_nodes) - set(bottom_nodes_v)))
        lst_common_movies = list(set(top_nodes) - (set(top_nodes) - set(top_nodes_v)))
        test_users = random.sample(lst_common_users, k = n_test_users)

        # a table test_users * new_movies (movies in the new dataset-can also exist in the first dataset)
        # but obviously the edges are totally new in the new dataset
        lst_users = [];                              lst_users_all = []
        lst_movies = [];                             lst_movies_all = []
        lst_predict = [];                            lst_predict_all = []
        lst_real = [];                               lst_real_all = []
        lst_ratios = [];                             lst_ratios_all = []
        lst_total_reviews_for_movies = [];           lst_total_reviews_for_movies_all = []
        lst_total_reviews_for_movies_old = [];       lst_total_reviews_for_movies_old_all = []
        lst_total_reviews_for_movies_new = [];       lst_total_reviews_for_movies_new_all = []
        lst_total_OLD_edges_for_users = [];          lst_total_OLD_edges_for_users_all = []
        lst_total_NEW_edges_for_users = [];          lst_total_NEW_edges_for_users_all = []

        # test a single user
        #test_users = ['A15BIF2J5V7IHZ']

        print('FOR loop starts in top-K users: {}'.format(datetime.datetime.now()))
        movie_FOR_reference_user = list(top_nodes_v)
        
        # test_users are the users we will predict their future movies
        for i, user in enumerate(test_users):
            ref_user_idx = node_list.index(user) 
            R = np.zeros(n_nodes); R[ref_user_idx] = 1
            R_zero = R.copy()
            movie_FOR_reference_user_unique = movie_FOR_reference_user.copy()
            
            # we shouldn't check a movie which has already been reviewed by the user
            for mv in lst_common_movies:
                try:
                    if max_connected_gr_amazon_movies.has_edge(user, mv):
                        movie_FOR_reference_user_unique.remove(mv)
                except:
                    if self.debug_mode == 'On':
                        print('Movie {} has not been reviewed by user {} in the first (modeling) dataset.'.format(mv, user))
            
            # let's see it for the last user, too: n_test_users - 1
            if i % 10 == 0 or i == n_test_users - 1:
                print('{}. of {} Random walk starts for {}-{} at {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))
            
            if self.debug_mode == 'On':
                print('{}. Random walk starts for {}-{} at {}'.format(i, ref_user_idx, user, datetime.datetime.now()))
            #R_vector = grpComp.random_walk_vector(P_norm, R[ref_user_idx], R_zero[ref_user_idx], beta=beta, n_steps=walk_steps)
            R_vector = grpComp.random_walk_vector(P_norm, R, R_zero, beta=beta, n_steps=walk_steps)

            '''
            # similarity_check_vector_VAL is doing the entire check for both the modeling dataset and the new dataset
            # a user can have an edge in the new dataset, too. since we predict 1 user-movie connection at a time,
            # we use the new data, as well. this approach is open to the discussion.
            # if we consider a missing edge, this approach should be fine but if we totally need to find ALL edges at once,
            # then we shouldn't consider the new edges in calculations
            # so we don't do re-modeling from scratch but we take advantage of the existing (new) edges to evaluate
            df_summary, movie_list_ref, movie_by_reference_user, similar_users = \
            grpComp.similarity_check_vector(R_vector, max_connected_gr_amazon_movies, movie_indexes,\
                                            ref_user_idx, node_list, top_similarity = top_neighbor)
            '''

            if self.debug_mode == 'On':
                print('similarity_check_vector_VAL starts for {}-{} at {}'.format(ref_user_idx, user, datetime.datetime.now()))
            ### check below if needed.. or if above needed..
            df_summary_v, movie_list_ref_v, movie_by_reference_user_v, user_similarity_top_non_zero = \
            grpComp_v.similarity_check_vector_VAL(R_vector, movie_indexes, ref_user_idx, node_list, node_list_v, \
            movie_FOR_reference_user_unique, max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, top_similarity=top_neighbor)

            self.df_summary_v = df_summary_v
            '''
            # this is to see the ratio in the modeling dataset, not required for the prediction phase
            # but can be checked to see the performance in the modeling dataset
            df_summary_ratio = \
            grpComp.similarity_summary_ratio(df_summary, movie_list_ref, max_connected_gr_amazon_movies, \
                                             movie_by_reference_user)
            '''

            if self.debug_mode == 'On':
                print('similarity_summary_ratio_VAL starts for {}-{} at {}'.format(ref_user_idx, user, datetime.datetime.now()))

                print('**********************************************')
            df_summary_ratio_v = \
            grpComp_v.similarity_summary_ratio_VAL(df_summary_v, movie_list_ref_v, \
                                     max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL)
            
            self.df_summary_ratio_v = df_summary_ratio_v
            
            # let's see it for the last user, too: n_test_users - 1
            if i % 10 == 0 or i == n_test_users - 1:
                print('Calculate the ratios per movie: {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))

            if self.debug_mode == 'On':
                print('Calculate the ratios per movie: {}'.format(i, n_test_users, ref_user_idx, user, datetime.datetime.now()))
              
            # ****************************************************************************************************
            # ****************************************************************************************************
            # ***** we will ONLY consider the top_N SUGGESTIONS instead of considering the WHOLE NEW DATASET *****
            df_summary_ratio_v_TOPN = df_summary_ratio_v.sort_values(by='ratio_similar', ascending=False).head(top_N_suggestions)
            lst_top_movie_suggestions = df_summary_ratio_v_TOPN['movie'].tolist()
                
            # we will iterate in the new movies - TOP-N
            for mv_new in lst_top_movie_suggestions:
                # ratio in the summary view for a specific movie (will always return 1 record since we give the mean 
                # in the summmary view, so values[0])=first and only row is picked.. 2nd volumn is the ratio_m
                ratio_m = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[1]
                lst_ratios.append(ratio_m)    
                
                # how many times this movie reiewed 
                review_m = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[2]
                lst_total_reviews_for_movies.append(review_m)
                
                # how many times this movie reiewed - in the OLD (modeling) dataset
                review_m_old = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[3]
                lst_total_reviews_for_movies_old.append(review_m_old)
                
                # how many times this movie reiewed - in the NEW (TEST) dataset
                review_m_new = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[4]
                lst_total_reviews_for_movies_new.append(review_m_new)

                lst_users.append(user)
                lst_movies.append(mv_new)
                
                predict_calc = 1 if ratio_m > threshold else 0
                lst_predict.append(predict_calc)
                
                real_m = max_connected_gr_amazon_movies_VAL.has_edge(user, mv_new)
                lst_real.append(1 if real_m==True else 0)
       
                edge_old = len(max_connected_gr_amazon_movies.edges(user))
                lst_total_OLD_edges_for_users.append(edge_old)
        
                edge_new = len(max_connected_gr_amazon_movies_VAL.edges(user))
                lst_total_NEW_edges_for_users.append(edge_new)
                
                
            # *****************************************************************************************
            # *****************************************************************************************
            # ***** we will check ALL movies in DATASET-2 in this part, not only top_N SUGGESTIONS ****
            # that's why, we will return 2 FINAL dataframes
                
            # we will iterate in the new movies - ALL
            for mv_new in movie_FOR_reference_user_unique:
                # ratio in the summary view for a specific movie (will always return 1 record since we give the mean 
                # in the summmary view, so values[0])=first and only row is picked.. 2nd volumn is the ratio_m
                ratio_m_all = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[1]
                lst_ratios_all.append(ratio_m_all)    
                
                # how many times this movie reiewed 
                review_m_all = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[2]
                lst_total_reviews_for_movies_all.append(review_m_all)
                
                # how many times this movie reiewed - in the OLD (modeling) dataset
                review_m_old_all = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[3]
                lst_total_reviews_for_movies_old_all.append(review_m_old_all)
                
                # how many times this movie reiewed - in the NEW (TEST) dataset
                review_m_new_all = df_summary_ratio_v.query("movie=='" + mv_new + "'").values[0].tolist()[4]
                lst_total_reviews_for_movies_new_all.append(review_m_new_all)

                lst_users_all.append(user)
                lst_movies_all.append(mv_new)
                
                predict_calc_all = 1 if ratio_m_all > threshold else 0
                lst_predict_all.append(predict_calc_all)
                
                real_m_all = max_connected_gr_amazon_movies_VAL.has_edge(user, mv_new)
                lst_real_all.append(1 if real_m_all == True else 0)
       
                edge_old_all = len(max_connected_gr_amazon_movies.edges(user))
                lst_total_OLD_edges_for_users_all.append(edge_old_all)
        
                edge_new_all = len(max_connected_gr_amazon_movies_VAL.edges(user))
                lst_total_NEW_edges_for_users_all.append(edge_new_all)
                   
        grpComp_v.movie_user_compare_datasets(top_nodes_v, top_nodes, bottom_nodes_v, bottom_nodes)

        dict_FINAL = {'user': lst_users, 'movie': lst_movies, 'prediction': lst_predict, 'reality': lst_real, 
                        'ngbr_ratio': lst_ratios, 'tot_rev_m': lst_total_reviews_for_movies, 
                      'tot_rev_m_OLD': lst_total_reviews_for_movies_old, 'tot_rev_m_NEW': lst_total_reviews_for_movies_new,
                      'n_old_edge': lst_total_OLD_edges_for_users, 'n_new_edge': lst_total_NEW_edges_for_users}
        
        dict_FINAL_all = {'user': lst_users_all, 'movie': lst_movies_all, 'prediction': lst_predict_all, 
                   'reality': lst_real_all, 'ngbr_ratio': lst_ratios_all, 'tot_rev_m': lst_total_reviews_for_movies_all, 
                  'tot_rev_m_OLD': lst_total_reviews_for_movies_old_all, 'tot_rev_m_NEW': lst_total_reviews_for_movies_new_all,
                   'n_old_edge': lst_total_OLD_edges_for_users_all, 'n_new_edge': lst_total_NEW_edges_for_users_all}

        df_FINAL = pd.DataFrame(dict_FINAL)
        df_FINAL_all = pd.DataFrame(dict_FINAL_all)
        
        end_time = datetime.datetime.now()
        print('**********************************************')
        print('Calculation time for run_validation_TOP_N: {}'.format(end_time-start_time))

        # save the necessary info to files to avoid repeating the calculations - PART-1
        # max_connected_gr_amazon_movies, max_connected_gr_amazon_movies_VAL, P_norm
        '''
        MovieGraph_1 = nx.to_numpy_matrix(max_connected_gr_amazon_movies)
        MovieGraph_1_val = nx.to_numpy_matrix(max_connected_gr_amazon_movies)

        from tempfile import TemporaryFile
        outfile_MovieGraph_1 = TemporaryFile()
        '''
        
        return df_FINAL, df_FINAL_all
    
    #def top_N_suggestions(self, df_FINAL, test_users, top_N_suggestions=10):
        

    # if we don't convert to string, if check doesn't recognize numpy but np as we defined earlier
    # however, some people might choose to give something else than np as a short name
    # converting to string fixes this conflict
    def save_objects_to_file(self, input_obj, file_name_to_save = 'outfile'):
        # we might remove the import from here
        #from tempfile import TemporaryFile
        #outfile = TemporaryFile()
        #file_name_to_save = 'outfile'
        if str(type(input_obj)) == "<class 'networkx.classes.graph.Graph'>":
            #print(type(input_obj))
            grp_sample = nx.to_numpy_matrix(input_obj)
            np.save(file_name_to_save, grp_sample)
            print('your graph is saved in matrix format')
        elif str(type(input_obj)) == "<class 'numpy.matrix'>":
            #print(type(input_obj))
            np.save(file_name_to_save, input_obj)
            print('your matrix is saved')
        elif str(type(input_obj)) == "<class 'pandas.core.frame.DataFrame'>":
            df_FINAL.to_csv(file_name_to_save)
            print('your dataframe is saved')
        else:
            str_type_graph = "<class 'networkx.classes.graph.Graph'>"
            str_type_matrix = "<class 'numpy.matrix'>"
            str_type_dataframe = "<class 'pandas.core.frame.DataFrame'>"
            print('Be sure that you are using NUMPY as np and PANDAS as pd')
            print('The type of the object is not supported: {}'.format(str(type(input_obj))))
            print('Supported types:\n{}\n{}\n{}'.format(str_type_graph, str_type_matrix, str_type_dataframe))

    def load_objects_from_file(self, output_obj = 'matrix', file_name_to_read = 'inputfile'):
        # we might remove the import from here
        #from tempfile import TemporaryFile
        #outfile = TemporaryFile()
        #file_name_to_save = 'outfile'
        if output_obj == "graph":
            #print(type(input_obj))
            file_name_to_read = 'Test_1/outfile_max_connected_gr_amazon_movies.npy'
            matrix_sample = np.load(file_name_to_read)
            grp_loaded = nx.from_numpy_matrix(matrix_sample)
            return grp_loaded
            print('your graph is loaded')
        elif output_obj == "matrix":
            #print(type(input_obj))
            file_name_to_read = 'Test_1/P_norm.npy'
            matrix_loaded = np.load(file_name_to_read)
            return matrix_loaded
            print('your matrix is loaded')
        elif output_obj == "dataframe":
            file_name_to_read = 'Test_1/outfile_df_FINAL'
            df_FINAL_loaded = pd.read_csv(file_name_to_read) 
            return df_FINAL_loaded
            print('your dataframe is loaded')
        else:
            str_type_graph = "graph"
            str_type_matrix = "matrix"
            str_type_dataframe = "dataframe"
            print('Be sure that you are using: NUMPY as np ... PANDAS as pd ... NETWORKX as nx')
            print('The type of the object is not supported: {}'.format(str(type(output_obj))))
            print('Supported types:\n{}\n{}\n{}'.format(str_type_graph, str_type_matrix, str_type_dataframe))

    def save_parameter_used(self, parameter_list, file_name='parameter_list.csv'):
        # put it to the top not in the function maybe
        import csv
        #with open(file_name, 'w', newline='') as myfile:
        with open(file_name, 'w', newline='\n') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(parameter_list)
            
    # threshold can be adjusted since the ratio is already provided
    #threshold = 10
    def final_summary(self, df_FINAL):
        tp = len(df_FINAL.query("prediction==1 and reality==1").values)
        fp = len(df_FINAL.query("prediction==1 and reality==0").values)
        tn = len(df_FINAL.query("prediction==0 and reality==0").values)
        fn = len(df_FINAL.query("prediction==0 and reality==1").values)

        acc = (tp + tn)/(tp + tn + fp + fn)
        
        ppv = tp/(tp + fp) # precision - positive predictive value **********
        tpr = tp/(tp + fn) # sensitivity, recall                   **********
        fpr = fp/(fp + tn)
        
        tnr = tn/(tn + fp) # sprecifity 
        fnr = fn/(fn + tp)
        
        f1 = (2*tp)/(2*tp + fp + fn)
        
        #print('tp={} .. fp={} .. tn={} .. fn={}'.format(tp, fp, tn, fn, acc))
        #print('acc={} .. tpr={} .. f1={}'.format(acc, tpr, f1))
        #print('fpr={} .. tnr={} .. ppv={}'.format(fpr, tnr, ppv))
        
        return acc, tpr, fpr, tnr, fnr, ppv, f1
    
    def final_summary_threshold_based(self, df_FINAL, threshold):
        df_FINAL_copy = df_FINAL.copy()
        for i in range(len(df_FINAL_copy)):
            df_FINAL_copy.loc[i, 'prediction'] = 1 if df_FINAL_copy.loc[i, 'ngbr_ratio'] > threshold else 0            
            '''
            if df_FINAL_copy.loc[i, 'ngbr_ratio'] > threshold:
                df_FINAL_copy.loc[i, 'prediction'] = 1
            else:
                df_FINAL_copy.loc[i, 'prediction'] = 0
            '''
        
        tp = len(df_FINAL_copy.query("prediction==1 and reality==1").values)
        fp = len(df_FINAL_copy.query("prediction==1 and reality==0").values)
        tn = len(df_FINAL_copy.query("prediction==0 and reality==0").values)
        fn = len(df_FINAL_copy.query("prediction==0 and reality==1").values)

        acc = (tp + tn)/(tp + tn + fp + fn)
        
        # in case of divicison by zero, we will have try-except blocks here
        try:
            ppv = tp/(tp + fp) # precision - positive predictive value **********
        except:
            ppv = 0
        try:
            tpr = tp/(tp + fn) # sensitivity, recall                   **********
        except:
            tpr = 0
        try:
            fpr = fp/(fp + tn)
        except:
            fpr = 0
            
        try:
            tnr = tn/(tn + fp) # specifity 
        except:
            tnr = 0
            
        try:
            fnr = fn/(fn + tp)
        except:
            fnr = 0
        
        try:
            f1 = (2*tp)/(2*tp + fp + fn)
        except:
            f1 = 0
        
        #print('tp={} .. fp={} .. tn={} .. fn={}'.format(tp, fp, tn, fn, acc))
        #print('acc={} .. tpr={} .. f1={}'.format(acc, tpr, f1))
        #print('fpr={} .. tnr={} .. ppv={}'.format(fpr, tnr, ppv))
        
        return acc, tpr, fpr, tnr, fnr, ppv, f1

    def save_performance_values(self, df_FINAL, time_1, time_2):
        '''
        lst_tot_rev_m = df_FINAL.loc[:, 'tot_rev_m'].values.tolist()
        lst_nbr_ratio = df_FINAL.loc[:, 'ngbr_ratio'].values.tolist()
        lst_n_old_edge = df_FINAL.loc[:, 'n_old_edge'].values.tolist()
        lst_n_new_edge = df_FINAL.loc[:, 'n_new_edge'].values.tolist()
        '''
        start_time_performance = datetime.datetime.now()
        lst_true_val = df_FINAL.loc[:, 'reality'].values.tolist()
        lst_ratio_val = df_FINAL.loc[:, 'ngbr_ratio'].values.tolist()

        fpr, tpr, thresholds = metrics.roc_curve(lst_true_val, lst_ratio_val)  #, pos_label=2
        lst_tpr = list(tpr); lst_fpr = list(fpr); lst_thresholds = list(thresholds) 
               
        #len_tpr = len(lst_tpr)
        #lst_precision = np.zeros(len_tpr)
        #lst_recall = np.zeros(len_tpr)
        
        #for i in range(len(lst_tpr)):
         #   lst_precision[i] = lst_tpr[i]/(lst_tpr[i] + lst_fpr[i])
         
        params_df = self.show_parameters_in_use()
        lst_name = list(params_df.loc[:, 'Name'])
        lst_value = list(params_df.loc[:, 'Value'])
        #lst_info = list(params_df.loc[:, 'Info'])
        
        #acc, tpr, fpr, tnr, ppv, f1 = final_summary(df_FINAL_copy) # 7 comes from here, 6 + threshold
        max_lst_length = max(len(lst_tpr), len(lst_name), 6)   

        roc_auc = roc_auc_score(lst_true_val, lst_ratio_val)
        #precision = pre
        
        lst_auc = list(np.zeros(max_lst_length, str))
        lst_auc[0] = roc_auc
        
        lst_presicion_based = []
        
        for t in lst_thresholds:
            acc, tpr, fpr, tnr, fnr, ppv, f1 = self.final_summary_threshold_based(df_FINAL, t)
            lst_t = [t,  acc, tpr, fpr, tnr, fnr, ppv, f1]
            lst_presicion_based.append(lst_t)
            
        max_i = 0
        max_i_val = 0
        
        lst_precision = list(np.zeros(max_lst_length, str))
        for i, l in enumerate(lst_presicion_based):
            p_precision = round(l[-2], 6)
            p_recall = round(l[2], 6)
            
            lst_precision[i] = p_precision           
            if p_precision > 0.3 and p_recall > 0.3 and p_precision > max_i:
                #max_i_val = l[-2]
                max_i = i
            elif p_precision > 0.3 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.3 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.1 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.1 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
        
        '''
        lst_precision = []
        for i, l in enumerate(lst_presicion_based):
            p_precision = round(l[-2], 6)
            p_recall = round(l[2], 6)
            
            lst_precision.append(p_precision)            
            if p_precision > 0.3 and p_recall > 0.3 and p_precision > max_i:
                #max_i_val = l[-2]
                max_i = i
            elif p_precision > 0.3 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.3 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.1 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.1 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
        '''

        #acc, tpr, fpr, tnr, fnr, ppv, f1, precision = self.final_summary(df_FINAL_copy)
        lst_other_metrics_name = list(np.zeros(max_lst_length, str))
        lst_other_metrics_value = list(np.zeros(max_lst_length, str))
        lst_other_metrics_name_prep = ['threshold',  'acc', 'tpr', 'fpr', 'tnr', 'fnr', 'precision', 'f1']
        #lst_other_metrics_value_prep = [threshold,  acc, tpr, fpr, tnr, fnr, ppv, f1]
        lst_other_metrics_value_prep = lst_presicion_based[max_i]
        lst_value[7] = lst_other_metrics_value_prep[0]
        
        for i, val in enumerate(lst_other_metrics_name_prep):
            lst_other_metrics_name[i] = val
        for i, val in enumerate(lst_other_metrics_value_prep):
            lst_other_metrics_value[i] = val
        
        
        end_time_performance = datetime.datetime.now()
        total_time_performance = end_time_performance - start_time_performance
        
        lst_calc_time = list(np.zeros(max_lst_length, str))
        lst_calc_time[0] = 'Graph Creation'; lst_calc_time[1] = time_1; 
        lst_calc_time[2] = 'Random Walk & Prediction'; lst_calc_time[3] = time_2; 
        lst_calc_time[4] = 'Threshold search'; lst_calc_time[5] = total_time_performance;
        lst_calc_time[6] = 'TOTAL TIME'; lst_calc_time[7] = time_1 + time_2 + total_time_performance
        
        if len(lst_name) < max_lst_length:
            diff_num = max_lst_length - len(lst_name)
            for i in range(diff_num):
                lst_name.append('')
                lst_value.append('')
                #lst_info.append('')
                
        if len(lst_tpr) < max_lst_length:
            diff_t = max_lst_length - len(lst_tpr)
            for i in range(diff_t):
                lst_tpr.append('')
                lst_fpr.append('')
                lst_thresholds.append('')
        
        
        total_reviews = 0
        # total number of reviews that those 100 test users did in dataset-2
        for u in df_FINAL['user'].unique():
            n_movie_reviewed_new = df_FINAL.query("user == '" + u + "'")['n_new_edge'].values[0]
            total_reviews += n_movie_reviewed_new
        
        # total number of TP (we recommended and indeed they reviewed it) for all users in dataset-2
        total_TP = lst_true_val.count(1)
        total_FN = total_reviews - total_TP
        total_FP = lst_true_val.count(0)
        
        decision4_precision = total_TP/(total_TP + total_FP)
        decision4_recall = total_TP/total_reviews
        
        lst_auc.append('decision_4'); lst_tpr.append(decision4_recall); lst_precision.append(decision4_precision)
        lst_fpr.append('');  lst_thresholds.append('');  lst_calc_time.append('');  lst_name.append('');  
        lst_value.append('');  lst_other_metrics_name.append('');  lst_other_metrics_value.append('');
        
        '''
        print(lst_auc)
        print(lst_tpr)
        print(lst_precision)
        print(lst_fpr)
        print(lst_thresholds)
        print(lst_calc_time)
        print(lst_name)
        print(lst_value)
        print(lst_other_metrics_name)
        print(lst_other_metrics_value)
        '''
        
        dict_perf = {'AUC': lst_auc, 'TPR': lst_tpr, 'Precision': lst_precision, 'FPR': lst_fpr, 'Thresholds': lst_thresholds,
                     'Calc_Time': lst_calc_time, 'lst_name': lst_name, 'lst_value': lst_value,
                    'other_metrics': lst_other_metrics_name, 'metrics_val': lst_other_metrics_value}
        
        df_perf = pd.DataFrame(dict_perf)
        
        file_prefix = "RESULTS/PerformanceValues_" + str(round(roc_auc,4)) + "_" 
        fileName_Perf = prs.FileNameUnique(prefix = file_prefix, suffix = '.csv')
        #fileName_Details = prs.FileNameUnique(prefix = "PredictionDetails_", suffix = '.csv')
        
        df_perf.to_csv(fileName_Perf)
        print('Performance Values are saved in {}'.format(fileName_Perf))
        
        #df_FINAL.to_csv(fileName_Details)
        #print('Prediction Details are saved in {}'.format(fileName_Details))
        
        return df_perf
        
    def save_performance_values_ALL(self, df_FINAL, time_1, time_2):
        '''
        lst_tot_rev_m = df_FINAL.loc[:, 'tot_rev_m'].values.tolist()
        lst_nbr_ratio = df_FINAL.loc[:, 'ngbr_ratio'].values.tolist()
        lst_n_old_edge = df_FINAL.loc[:, 'n_old_edge'].values.tolist()
        lst_n_new_edge = df_FINAL.loc[:, 'n_new_edge'].values.tolist()
        '''
        start_time_performance = datetime.datetime.now()
        lst_true_val = df_FINAL.loc[:, 'reality'].values.tolist()
        lst_ratio_val = df_FINAL.loc[:, 'ngbr_ratio'].values.tolist()

        fpr, tpr, thresholds = metrics.roc_curve(lst_true_val, lst_ratio_val)  #, pos_label=2
        lst_tpr = list(tpr); lst_fpr = list(fpr); lst_thresholds = list(thresholds) 
               
        #len_tpr = len(lst_tpr)
        #lst_precision = np.zeros(len_tpr)
        #lst_recall = np.zeros(len_tpr)
        
        #for i in range(len(lst_tpr)):
         #   lst_precision[i] = lst_tpr[i]/(lst_tpr[i] + lst_fpr[i])
         
        params_df = self.show_parameters_in_use()
        lst_name = list(params_df.loc[:, 'Name'])
        lst_value = list(params_df.loc[:, 'Value'])
        #lst_info = list(params_df.loc[:, 'Info'])
        
        #acc, tpr, fpr, tnr, ppv, f1 = final_summary(df_FINAL_copy) # 7 comes from here, 6 + threshold
        max_lst_length = max(len(lst_tpr), len(lst_name), 6)   

        roc_auc = roc_auc_score(lst_true_val, lst_ratio_val)
        #precision = pre
        
        lst_auc = list(np.zeros(max_lst_length, str))
        lst_auc[0] = roc_auc
        
        lst_presicion_based = []
        
        for t in lst_thresholds:
            acc, tpr, fpr, tnr, fnr, ppv, f1 = self.final_summary_threshold_based(df_FINAL, t)
            lst_t = [t,  acc, tpr, fpr, tnr, fnr, ppv, f1]
            lst_presicion_based.append(lst_t)
            
        max_i = 0
        max_i_val = 0
        
        lst_precision = list(np.zeros(max_lst_length, str))
        for i, l in enumerate(lst_presicion_based):
            p_precision = round(l[-2], 6)
            p_recall = round(l[2], 6)
            
            lst_precision[i] = p_precision           
            if p_precision > 0.3 and p_recall > 0.3 and p_precision > max_i:
                #max_i_val = l[-2]
                max_i = i
            elif p_precision > 0.3 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.3 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.2 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.2 and p_recall > 0.1 and p_precision > max_i:
                max_i = i
            elif p_precision > 0.1 and p_recall > 0.2 and p_precision > max_i:
                max_i = i

        #acc, tpr, fpr, tnr, fnr, ppv, f1, precision = self.final_summary(df_FINAL_copy)
        lst_other_metrics_name = list(np.zeros(max_lst_length, str))
        lst_other_metrics_value = list(np.zeros(max_lst_length, str))
        lst_other_metrics_name_prep = ['threshold',  'acc', 'tpr', 'fpr', 'tnr', 'fnr', 'precision', 'f1']
        #lst_other_metrics_value_prep = [threshold,  acc, tpr, fpr, tnr, fnr, ppv, f1]
        lst_other_metrics_value_prep = lst_presicion_based[max_i]
        lst_value[7] = lst_other_metrics_value_prep[0]
        
        for i, val in enumerate(lst_other_metrics_name_prep):
            lst_other_metrics_name[i] = val
        for i, val in enumerate(lst_other_metrics_value_prep):
            lst_other_metrics_value[i] = val
        
        
        end_time_performance = datetime.datetime.now()
        total_time_performance = end_time_performance - start_time_performance
        
        lst_calc_time = list(np.zeros(max_lst_length, str))
        lst_calc_time[0] = 'Graph Creation'; lst_calc_time[1] = time_1; 
        lst_calc_time[2] = 'Random Walk & Prediction'; lst_calc_time[3] = time_2; 
        lst_calc_time[4] = 'Threshold search'; lst_calc_time[5] = total_time_performance;
        lst_calc_time[6] = 'TOTAL TIME'; lst_calc_time[7] = time_1 + time_2 + total_time_performance
        
        if len(lst_name) < max_lst_length:
            diff_num = max_lst_length - len(lst_name)
            for i in range(diff_num):
                lst_name.append('')
                lst_value.append('')
                #lst_info.append('')
                
        if len(lst_tpr) < max_lst_length:
            diff_t = max_lst_length - len(lst_tpr)
            for i in range(diff_t):
                lst_tpr.append('')
                lst_fpr.append('')
                lst_thresholds.append('')
        
        '''
        total_reviews = 0
        # total number of reviews that those 100 test users did in dataset-2
        for u in df_FINAL['user'].unique():
            n_movie_reviewed_new = df_FINAL.query("user == '" + u + "'")['n_new_edge'].values[0]
            total_reviews += n_movie_reviewed_new
        
        # total number of TP (we recommended and indeed they reviewed it) for all users in dataset-2
        total_TP = lst_true_val.count(1)
        total_FN = total_reviews - total_TP
        total_FP = lst_true_val.count(0)
        
        
        decision4_precision = total_TP/(total_TP + total_FP)
        decision4_recall = total_TP/total_reviews
        
        lst_auc.append('decision_4'); lst_tpr.append(decision4_recall); lst_precision.append(decision4_precision)
        lst_fpr.append('');  lst_thresholds.append('');  lst_calc_time.append('');  lst_name.append('');  
        lst_value.append('');  lst_other_metrics_name.append('');  lst_other_metrics_value.append('');
        '''
        
        dict_perf = {'AUC': lst_auc, 'TPR': lst_tpr, 'Precision': lst_precision, 'FPR': lst_fpr, 'Thresholds': lst_thresholds,
                     'Calc_Time': lst_calc_time, 'lst_name': lst_name, 'lst_value': lst_value,
                    'other_metrics': lst_other_metrics_name, 'metrics_val': lst_other_metrics_value}
        
        df_perf = pd.DataFrame(dict_perf)
        
        file_prefix = "RESULTS/PerformanceValues_ALL_" + str(round(roc_auc,4)) + "_" 
        fileName_Perf = prs.FileNameUnique(prefix = file_prefix, suffix = '.csv')
        #fileName_Details = prs.FileNameUnique(prefix = "PredictionDetails_", suffix = '.csv')
        
        df_perf.to_csv(fileName_Perf)
        print('Performance Values are saved in {}'.format(fileName_Perf))
        
        #df_FINAL.to_csv(fileName_Details)
        #print('Prediction Details are saved in {}'.format(fileName_Details))
        
        return df_perf