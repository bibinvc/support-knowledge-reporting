using System;
using System.IO;
using System.Net;
using System.Text;
using System.Collections.Generic;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;

[DataContract]
public class Row {
    [DataMember(Name="status", IsRequired=true)] public string Status;
    [DataMember(Name="count", IsRequired=true)] public int Count;
}
[DataContract]
public class Report {
    [DataMember(Name="schema_version", IsRequired=true)] public int Version;
    [DataMember(Name="synthetic", IsRequired=true)] public bool Synthetic;
    [DataMember(Name="total", IsRequired=true)] public int Total;
    [DataMember(Name="rows", IsRequired=true)] public Row[] Rows;
}
public static class ReportTool {
    private static byte[] Bounded(Stream input) {
        using (MemoryStream output=new MemoryStream()) {
            byte[] buffer=new byte[1024]; int n;
            while ((n=input.Read(buffer,0,buffer.Length))>0) {
                if(output.Length+n>8192) throw new InvalidDataException("Report exceeds 8192 bytes");
                output.Write(buffer,0,n);
            }
            return output.ToArray();
        }
    }
    private static void Validate(Report data) {
        if(data==null || data.Version!=1 || !data.Synthetic || data.Total<0 || data.Total>100000 || data.Rows==null || data.Rows.Length!=4)
            throw new InvalidDataException("Expected a version-1 synthetic report");
        HashSet<string> allowed=new HashSet<string>(new string[]{"Open","In progress","Resolved","Closed"});
        int total=0;
        foreach(Row row in data.Rows) {
            if(row==null || !allowed.Remove(row.Status) || row.Count<0 || row.Count>100000)
                throw new InvalidDataException("Invalid or duplicate status/count");
            total=checked(total+row.Count);
        }
        if(total!=data.Total) throw new InvalidDataException("Counts do not match the stated total");
    }
    public static int Main(string[] args) {
        try {
            byte[] bytes; string destination;
            if(args.Length==3 && args[0]=="--input-json") {
                using(FileStream input=File.OpenRead(args[1])) bytes=Bounded(input);
                destination=args[2];
            } else if(args.Length==2) {
                Uri uri;
                if(!Uri.TryCreate(args[0],UriKind.Absolute,out uri) || uri.Scheme!="http" || uri.Host!="127.0.0.1" || uri.IsDefaultPort || uri.UserInfo!="" || uri.Fragment!="" || uri.Query!="")
                    throw new InvalidDataException("Use an explicit owned loopback HTTP fixture");
                HttpWebRequest request=(HttpWebRequest)WebRequest.Create(uri);
                request.AllowAutoRedirect=false; request.Proxy=null; request.Timeout=3000; request.ReadWriteTimeout=3000;
                using(HttpWebResponse response=(HttpWebResponse)request.GetResponse()) {
                    if(response.StatusCode!=HttpStatusCode.OK) throw new InvalidDataException("Expected HTTP 200; redirects are not followed");
                    using(Stream input=response.GetResponseStream()) bytes=Bounded(input);
                }
                destination=args[1];
            } else throw new ArgumentException("ReportTool URL OUTPUT.csv or --input-json INPUT.json OUTPUT.csv");
            Report report;
            using(MemoryStream input=new MemoryStream(bytes)) report=(Report)new DataContractJsonSerializer(typeof(Report)).ReadObject(input);
            Validate(report);
            StringBuilder csv=new StringBuilder("status,count\n");
            foreach(Row row in report.Rows) csv.Append(row.Status).Append(',').Append(row.Count).Append('\n');
            csv.Append("Total,").Append(report.Total).Append('\n');
            File.WriteAllText(destination,csv.ToString(),new UTF8Encoding(false));
            Console.WriteLine("Validated synthetic report exported: "+report.Total+" incidents");
            return 0;
        } catch(Exception error) {
            Console.Error.WriteLine(error.Message); return 2;
        }
    }
}
