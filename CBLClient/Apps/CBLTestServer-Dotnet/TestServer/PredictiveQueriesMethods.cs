// 
//  DocumentMethods.cs
// 
//  Author:
//   Sridevi Saragadam  <sridevi.saragadam@couchbase.com>
// 
//  Copyright (c) 2017 Couchbase, Inc All rights reserved.
// 
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
// 
//  http://www.apache.org/licenses/LICENSE-2.0
// 
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// 

using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Net;

using JetBrains.Annotations;

using Couchbase.Lite.Enterprise.Query;

using static Couchbase.Lite.Testing.DatabaseMethods;
using static Couchbase.Lite.Query.QueryBuilder;
using Couchbase.Lite.Util;
using Couchbase.Lite.Query;

namespace Couchbase.Lite.Testing
{
    internal static class PredictiveQueriesMethods
    {
        #region Public Methods
        public static void RegisterModel([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            String modelName = postBody["model_name"].ToString();
            EchoModel echoModel = new EchoModel(modelName);
            Database.Prediction.RegisterModel(modelName, echoModel);
            response.WriteBody(MemoryMap.Store(echoModel));
        }

        public static void UnRegisterModel([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            String modelName = postBody["model_name"].ToString();
            Database.Prediction.UnregisterModel(modelName);
            response.WriteEmptyBody();
        }

        internal static void GetPredictionQueryResult([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<EchoModel>(postBody, "model", model =>
                {
                    Dictionary<String, Object> dict = (Dictionary< String, Object>)postBody["dictionary"];
                    IExpression input = Expression.Value(dict);
                    IPredictionFunction prediction = Function.Prediction(model.name, input);
                    List<Object> resultArray = new List<Object>();
                    using (IQuery query = QueryBuilder
                           .Select(SelectResult.Expression(prediction))
                           .From(DataSource.Database(db)))
                        foreach (Result row in query.Execute())
                        {
                            resultArray.Add(row.ToDictionary());
                        }
                    response.WriteBody(resultArray);
                });
            });
        }

        internal static void NonDictionary([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                With<EchoModel>(postBody, "model", model =>
                {
                    var dict = postBody["nonDictionary"];
                    IExpression input = Expression.Value(dict);
                    IPredictionFunction prediction = Function.Prediction(model.name, input);
                    List<Object> resultArray = new List<Object>();
                    using (IQuery query = QueryBuilder
                           .Select(SelectResult.Expression(prediction))
                           .From(DataSource.Database(db)))
                        try
                        {
                            query.Execute();
                        }
                        catch (Exception e)
                        {
                            response.WriteBody(e.Message);
                        }
                });
            });
        }

        public static void GetNumberOfCalls([NotNull] NameValueCollection args,
                                  [NotNull] IReadOnlyDictionary<string, object> postBody,
                                  [NotNull] HttpListenerResponse response)
        {
            With<EchoModel>(postBody, "model", model =>
            {
                response.WriteBody(model.NumberOfCalls);
            });
        }

        internal static void GetEuclideanDistance([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                String key1 = postBody["key1"].ToString();
                String key2 = postBody["key2"].ToString();
                IExpression distance = Function.EuclideanDistance(Expression.Property(key1), Expression.Property(key2));
                List<Object> resultArray = new List<Object>();
                using (IQuery query = QueryBuilder
                       .Select(SelectResult.Expression(distance))
                       .From(DataSource.Database(db)))
                foreach (Result row in query.Execute())
                {
                      resultArray.Add(row.ToDictionary());
                }
                response.WriteBody(resultArray);
            });
        }

        internal static void GetSquaredEuclideanDistance([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                String key1 = postBody["key1"].ToString();
                String key2 = postBody["key2"].ToString();
                IExpression distance = Function.SquaredEuclideanDistance(Expression.Property(key1), Expression.Property(key2));
                List<Object> resultArray = new List<Object>();
                using (IQuery query = QueryBuilder
                       .Select(SelectResult.Expression(distance))
                       .From(DataSource.Database(db)))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }

        internal static void GetCosineDistance([NotNull] NameValueCollection args,
            [NotNull] IReadOnlyDictionary<string, object> postBody,
            [NotNull] HttpListenerResponse response)
        {
            With<Database>(postBody, "database", db =>
            {
                String key1 = postBody["key1"].ToString();
                String key2 = postBody["key2"].ToString();
                IExpression distance = Function.CosineDistance(Expression.Property(key1), Expression.Property(key2));
                List<Object> resultArray = new List<Object>();
                using (IQuery query = QueryBuilder
                       .Select(SelectResult.Expression(distance))
                       .From(DataSource.Database(db)))
                    foreach (Result row in query.Execute())
                    {
                        resultArray.Add(row.ToDictionary());
                    }
                response.WriteBody(resultArray);
            });
        }
        #endregion
    }

    internal sealed class EchoModel : IPredictiveModel
    {
        public int NumberOfCalls { get; private set; }
        public string name;

        public EchoModel(String name)
        {
            this.name = name;
        }

        public String GetName()
        {
            return name;
        }
        public DictionaryObject Predict(DictionaryObject input)
        {
            NumberOfCalls++;
            return input;
        }


    }
}